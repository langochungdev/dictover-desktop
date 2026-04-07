use arboard::{Clipboard, ImageData};
use enigo::{Direction, Enigo, Key, Keyboard, Mouse, Settings};
use std::borrow::Cow;
#[cfg(target_os = "windows")]
use std::ffi::c_void;
#[cfg(target_os = "windows")]
use std::sync::{Mutex, OnceLock};
use std::time::{SystemTime, UNIX_EPOCH};
use std::{thread, time::Duration};

#[cfg(target_os = "windows")]
use windows::core::PCWSTR;
#[cfg(target_os = "windows")]
use windows::Win32::Foundation::{LPARAM, WPARAM};
#[cfg(target_os = "windows")]
use windows::Win32::UI::Input::KeyboardAndMouse::{
    ActivateKeyboardLayout, GetKeyboardLayout, LoadKeyboardLayoutW, ACTIVATE_KEYBOARD_LAYOUT_FLAGS,
    HKL, KLF_ACTIVATE,
};
#[cfg(target_os = "windows")]
use windows::Win32::UI::WindowsAndMessaging::{
    GetForegroundWindow, GetWindowThreadProcessId, PostMessageW, INPUTLANGCHANGE_FORWARD,
    WM_INPUTLANGCHANGEREQUEST,
};

const ACTION_DELAY_MS: u64 = 80;
const COPY_DELAY_MS: u64 = 120;

#[cfg(target_os = "windows")]
static QUICK_CONVERT_PREVIOUS_LAYOUT: OnceLock<Mutex<Option<isize>>> = OnceLock::new();

fn new_enigo() -> Result<Enigo, String> {
    Enigo::new(&Settings::default()).map_err(|err| format!("create input controller failed: {err}"))
}

fn run_control_combo(enigo: &mut Enigo, key: Key) -> Result<(), String> {
    enigo
        .key(Key::Control, Direction::Press)
        .map_err(|err| format!("press control failed: {err}"))?;
    enigo
        .key(key, Direction::Click)
        .map_err(|err| format!("press key failed: {err}"))?;
    enigo
        .key(Key::Control, Direction::Release)
        .map_err(|err| format!("release control failed: {err}"))
}

enum ClipboardSnapshot {
    Text(String),
    Image {
        width: usize,
        height: usize,
        bytes: Vec<u8>,
    },
}

fn capture_clipboard_snapshot(clipboard: &mut Clipboard) -> Option<ClipboardSnapshot> {
    if let Ok(image) = clipboard.get_image() {
        return Some(ClipboardSnapshot::Image {
            width: image.width,
            height: image.height,
            bytes: image.bytes.into_owned(),
        });
    }

    if let Ok(text) = clipboard.get_text() {
        return Some(ClipboardSnapshot::Text(text));
    }

    None
}

fn restore_clipboard(clipboard: &mut Clipboard, previous: Option<ClipboardSnapshot>) {
    match previous {
        Some(ClipboardSnapshot::Text(snapshot)) => {
            let _ = clipboard.set_text(snapshot);
        }
        Some(ClipboardSnapshot::Image {
            width,
            height,
            bytes,
        }) => {
            let _ = clipboard.set_image(ImageData {
                width,
                height,
                bytes: Cow::Owned(bytes),
            });
        }
        None => {}
    }
}

fn clipboard_marker(prefix: &str) -> String {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|value| value.as_nanos())
        .unwrap_or(0);
    format!("__dictover_{prefix}_{nanos}__")
}

pub fn capture_selection_text() -> Result<String, String> {
    let mut clipboard = Clipboard::new().map_err(|err| format!("open clipboard failed: {err}"))?;
    let previous = capture_clipboard_snapshot(&mut clipboard);
    let marker = clipboard_marker("selection");
    let _ = clipboard.set_text(marker.clone());
    let mut enigo = new_enigo()?;

    run_control_combo(&mut enigo, Key::Unicode('c'))?;
    thread::sleep(Duration::from_millis(COPY_DELAY_MS));

    let selected = clipboard.get_text().unwrap_or_default();
    let resolved = if selected == marker {
        String::new()
    } else {
        selected
    };
    restore_clipboard(&mut clipboard, previous);
    Ok(resolved)
}

pub fn capture_active_document_text() -> Result<String, String> {
    let mut clipboard = Clipboard::new().map_err(|err| format!("open clipboard failed: {err}"))?;
    let previous = capture_clipboard_snapshot(&mut clipboard);
    let marker = clipboard_marker("document");
    let _ = clipboard.set_text(marker.clone());
    let mut enigo = new_enigo()?;

    run_control_combo(&mut enigo, Key::Unicode('a'))?;
    thread::sleep(Duration::from_millis(ACTION_DELAY_MS));
    run_control_combo(&mut enigo, Key::Unicode('c'))?;
    thread::sleep(Duration::from_millis(COPY_DELAY_MS));

    let selected = clipboard.get_text().unwrap_or_default();
    let resolved = if selected == marker {
        String::new()
    } else {
        selected
    };
    restore_clipboard(&mut clipboard, previous);
    Ok(resolved)
}

pub fn replace_active_document_text(replacement: &str) -> Result<(), String> {
    let mut clipboard = Clipboard::new().map_err(|err| format!("open clipboard failed: {err}"))?;
    let previous = capture_clipboard_snapshot(&mut clipboard);
    clipboard
        .set_text(replacement.to_owned())
        .map_err(|err| format!("write clipboard failed: {err}"))?;

    let mut enigo = new_enigo()?;
    run_control_combo(&mut enigo, Key::Unicode('a'))?;
    thread::sleep(Duration::from_millis(ACTION_DELAY_MS));
    run_control_combo(&mut enigo, Key::Unicode('v'))?;
    thread::sleep(Duration::from_millis(ACTION_DELAY_MS));

    restore_clipboard(&mut clipboard, previous);
    Ok(())
}

pub fn press_enter_key() -> Result<(), String> {
    let mut enigo = new_enigo()?;
    enigo
        .key(Key::Return, Direction::Click)
        .map_err(|err| format!("press enter failed: {err}"))?;
    Ok(())
}

pub fn cursor_position() -> Option<(i32, i32)> {
    let enigo = new_enigo().ok()?;
    enigo.location().ok()
}

#[cfg(target_os = "windows")]
fn previous_layout_slot() -> &'static Mutex<Option<isize>> {
    QUICK_CONVERT_PREVIOUS_LAYOUT.get_or_init(|| Mutex::new(None))
}

#[cfg(target_os = "windows")]
fn foreground_layout() -> Option<HKL> {
    let foreground = unsafe { GetForegroundWindow() };
    if foreground.0.is_null() {
        return None;
    }

    let thread_id = unsafe { GetWindowThreadProcessId(foreground, None) };
    if thread_id == 0 {
        return None;
    }

    Some(unsafe { GetKeyboardLayout(thread_id) })
}

#[cfg(target_os = "windows")]
pub fn capture_quick_convert_baseline_layout() -> Result<bool, String> {
    let Some(hkl) = foreground_layout() else {
        return Ok(false);
    };

    let mut guard = previous_layout_slot()
        .lock()
        .map_err(|_| "capture keyboard layout lock poisoned".to_owned())?;
    *guard = Some(hkl.0 as isize);
    Ok(true)
}

#[cfg(target_os = "windows")]
fn activate_layout(hkl: HKL) {
    let _ = unsafe { ActivateKeyboardLayout(hkl, ACTIVATE_KEYBOARD_LAYOUT_FLAGS(0)) };

    let foreground = unsafe { GetForegroundWindow() };
    if !foreground.0.is_null() {
        let _ = unsafe {
            PostMessageW(
                foreground,
                WM_INPUTLANGCHANGEREQUEST,
                WPARAM(INPUTLANGCHANGE_FORWARD as usize),
                LPARAM(hkl.0 as isize),
            )
        };
    }
}

#[cfg(target_os = "windows")]
pub fn activate_english_keyboard_layout() -> Result<bool, String> {
    let previous = foreground_layout();

    let mut layout = "00000409".encode_utf16().collect::<Vec<u16>>();
    layout.push(0);

    let hkl = unsafe { LoadKeyboardLayoutW(PCWSTR(layout.as_ptr()), KLF_ACTIVATE) }
        .map_err(|err| format!("load english keyboard layout failed: {err}"))?;

    if let Some(previous_hkl) = previous {
        if previous_hkl.0 != hkl.0 {
            if let Ok(mut guard) = previous_layout_slot().lock() {
                if guard.is_none() {
                    *guard = Some(previous_hkl.0 as isize);
                }
            }
        }
    }

    activate_layout(hkl);

    Ok(true)
}

#[cfg(target_os = "windows")]
pub fn restore_previous_keyboard_layout() -> Result<bool, String> {
    let stored = {
        let guard = previous_layout_slot()
            .lock()
            .map_err(|_| "restore keyboard layout lock poisoned".to_owned())?;
        *guard
    };

    let Some(raw_hkl) = stored else {
        return Ok(false);
    };

    let hkl = HKL(raw_hkl as *mut c_void);
    activate_layout(hkl);
    Ok(true)
}

#[cfg(not(target_os = "windows"))]
pub fn activate_english_keyboard_layout() -> Result<bool, String> {
    Ok(false)
}

#[cfg(not(target_os = "windows"))]
pub fn restore_previous_keyboard_layout() -> Result<bool, String> {
    Ok(false)
}

#[cfg(not(target_os = "windows"))]
pub fn capture_quick_convert_baseline_layout() -> Result<bool, String> {
    Ok(false)
}
