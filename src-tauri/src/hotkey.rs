use arboard::Clipboard;
use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_global_shortcut::GlobalShortcutExt;

use crate::bridge::{self, AppState, TranslatePayload};

#[derive(Debug, Clone, Serialize)]
pub struct HotkeyTranslationEvent {
    pub original: String,
    pub translated: String,
}

pub fn sanitize_inject(input: &str) -> String {
    input.replace('\r', "").trim().to_owned()
}

fn is_valid_modifier(token: &str) -> bool {
    matches!(
        token.to_ascii_lowercase().as_str(),
        "ctrl" | "control" | "shift" | "alt" | "cmd" | "meta" | "cmdorctrl" | "commandorcontrol"
    )
}

fn is_valid_key_token(token: &str) -> bool {
    if token.is_empty() {
        return false;
    }
    if token.len() == 1 {
        return token.chars().all(|ch| ch.is_ascii_alphanumeric());
    }
    if let Some(rest) = token.strip_prefix('F') {
        return !rest.is_empty() && rest.chars().all(|ch| ch.is_ascii_digit());
    }
    matches!(token.to_ascii_lowercase().as_str(), "space" | "enter" | "tab")
}

pub fn parse_hotkey(shortcut: &str) -> Result<(), String> {
    let parts: Vec<&str> = shortcut
        .split('+')
        .map(|part| part.trim())
        .filter(|part| !part.is_empty())
        .collect();
    if parts.len() < 2 {
        return Err("hotkey must include at least one modifier and one key".to_owned());
    }
    for modifier in &parts[..parts.len() - 1] {
        if !is_valid_modifier(modifier) {
            return Err(format!("unsupported modifier: {modifier}"));
        }
    }
    let key = parts[parts.len() - 1];
    if !is_valid_key_token(key) {
        return Err(format!("unsupported key: {key}"));
    }
    Ok(())
}

pub fn replace_registered_hotkey(app: &AppHandle, shortcut: &str) -> Result<(), String> {
    parse_hotkey(shortcut)?;
    let manager = app.global_shortcut();
    manager
        .unregister_all()
        .map_err(|err| format!("unregister hotkeys failed: {err}"))?;
    manager
        .register(shortcut)
        .map_err(|err| format!("register hotkey failed: {err}"))
}

pub async fn on_hotkey_triggered(app: AppHandle) -> Result<(), String> {
    let state = app.state::<AppState>();
    let config = {
        let guard = state
            .config
            .lock()
            .map_err(|_| "config lock poisoned".to_owned())?;
        guard.clone()
    };

    let mut clipboard = Clipboard::new().map_err(|err| format!("open clipboard failed: {err}"))?;
    let original = clipboard
        .get_text()
        .map_err(|err| format!("read clipboard failed: {err}"))?;
    let sanitized = sanitize_inject(&original);
    if sanitized.is_empty() {
        return Ok(());
    }

    let payload = TranslatePayload {
        text: sanitized.clone(),
        source: config.source_language,
        target: config.target_language,
    };

    let response = bridge::translate_via_sidecar(&state.client, payload).await?;
    clipboard
        .set_text(response.result.clone())
        .map_err(|err| format!("write clipboard failed: {err}"))?;

    let event = HotkeyTranslationEvent {
        original: sanitized,
        translated: response.result,
    };
    app.emit("hotkey-translated", event)
        .map_err(|err| format!("emit hotkey event failed: {err}"))
}

#[cfg(test)]
mod tests {
    use super::{parse_hotkey, sanitize_inject};

    #[test]
    fn test_sanitize_text_for_inject() {
        assert_eq!(sanitize_inject("hello\r\n"), "hello");
        assert_eq!(sanitize_inject("  spaces  "), "spaces");
    }

    #[test]
    fn test_hotkey_parse() {
        assert!(parse_hotkey("Ctrl+Shift+T").is_ok());
        assert!(parse_hotkey("invalid").is_err());
    }
}
