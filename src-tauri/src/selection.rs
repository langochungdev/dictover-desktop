use serde::Serialize;
use tauri::{AppHandle, Emitter};

#[derive(Debug, Clone, Serialize)]
pub struct SelectionEvent {
    pub text: String,
    pub trigger: String,
}

pub fn start_selection_listener(_app: AppHandle) {}

pub fn emit_selection_changed(app: &AppHandle, text: String, trigger: String) -> Result<(), String> {
    let payload = SelectionEvent { text, trigger };
    app.emit("selection-changed", payload)
        .map_err(|err| format!("emit selection event failed: {err}"))
}
