#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod bridge;
mod config;
mod hotkey;
mod selection;

use reqwest::Client;
use tauri::Manager;
use tauri_plugin_global_shortcut::{Builder as GlobalShortcutBuilder, ShortcutState};

fn main() {
    tauri::Builder::default()
        .plugin(
            GlobalShortcutBuilder::new()
                .with_handler(|app, _shortcut, event| {
                    if event.state() == ShortcutState::Pressed {
                        let app_handle = app.clone();
                        tauri::async_runtime::spawn(async move {
                            let _ = hotkey::on_hotkey_triggered(app_handle).await;
                        });
                    }
                })
                .build(),
        )
        .setup(|app| {
            let app_handle = app.handle().clone();
            let loaded = config::load_config_from_disk(&app_handle);
            let state = bridge::AppState {
                config: std::sync::Mutex::new(loaded.clone()),
                client: Client::new(),
            };
            app.manage(state);
            hotkey::replace_registered_hotkey(&app_handle, &loaded.hotkey_translate_shortcut)?;
            selection::start_selection_listener(app_handle);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            bridge::load_config,
            bridge::save_config,
            bridge::translate_text,
            bridge::lookup_dictionary,
            bridge::emit_selection_changed
        ])
        .run(tauri::generate_context!())
        .expect("error while running DictOver Desktop");
}
