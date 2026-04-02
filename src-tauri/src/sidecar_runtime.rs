use std::io::{Error, ErrorKind};
use std::process::{Child, Command};
use std::sync::{Mutex, OnceLock};
use tauri::{AppHandle, Manager};

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

const SIDECAR_PORT: &str = "49152";
const SIDECAR_HOST: &str = "127.0.0.1";
static SIDECAR_CHILD_SLOT: OnceLock<Mutex<Option<Child>>> = OnceLock::new();

#[cfg(target_os = "windows")]
const SIDECAR_BINARY_NAME: &str = "dictover-sidecar.exe";
#[cfg(not(target_os = "windows"))]
const SIDECAR_BINARY_NAME: &str = "dictover-sidecar";

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x08000000;

pub fn apply_default_sidecar_endpoints() {
    let base = format!("http://{SIDECAR_HOST}:{SIDECAR_PORT}");
    set_if_missing("SIDECAR_URL", &format!("{base}/translate"));
    set_if_missing("SIDECAR_LOOKUP_URL", &format!("{base}/lookup"));
    set_if_missing("SIDECAR_IMAGES_URL", &format!("{base}/images"));
    set_if_missing("SIDECAR_OCR_URL", &format!("{base}/ocr"));
}

pub fn start_release_sidecar(app: &AppHandle) -> Result<Option<Child>, Error> {
    apply_default_sidecar_endpoints();

    if cfg!(debug_assertions) {
        return Ok(None);
    }

    let resource_dir = app.path().resource_dir().map_err(|err| {
        Error::new(
            ErrorKind::Other,
            format!("resolve resource dir failed: {err}"),
        )
    })?;

    let sidecar_path = resource_dir.join("binaries").join(SIDECAR_BINARY_NAME);
    if !sidecar_path.exists() {
        return Err(Error::new(
            ErrorKind::NotFound,
            format!("sidecar binary not found at {}", sidecar_path.display()),
        ));
    }

    let mut command = Command::new(&sidecar_path);
    command
        .env("SIDECAR_HOST", SIDECAR_HOST)
        .env("SIDECAR_PORT", SIDECAR_PORT)
        .arg("--host")
        .arg(SIDECAR_HOST)
        .arg("--port")
        .arg(SIDECAR_PORT);

    #[cfg(target_os = "windows")]
    command.creation_flags(CREATE_NO_WINDOW);

    let child = command
        .spawn()
        .map_err(|err| Error::new(ErrorKind::Other, format!("spawn sidecar failed: {err}")))?;

    Ok(Some(child))
}

pub fn set_tracked_sidecar(child: Option<Child>) {
    let slot = sidecar_slot();
    if let Ok(mut guard) = slot.lock() {
        *guard = child;
    }
}

pub fn stop_tracked_sidecar() {
    let slot = sidecar_slot();
    if let Ok(mut guard) = slot.lock() {
        if let Some(mut child) = guard.take() {
            stop_sidecar(&mut child);
        }
    }
}

pub fn stop_sidecar(child: &mut Child) {
    let _ = child.kill();
    let _ = child.wait();
}

fn set_if_missing(key: &str, value: &str) {
    if std::env::var_os(key).is_none() {
        std::env::set_var(key, value);
    }
}

fn sidecar_slot() -> &'static Mutex<Option<Child>> {
    SIDECAR_CHILD_SLOT.get_or_init(|| Mutex::new(None))
}
