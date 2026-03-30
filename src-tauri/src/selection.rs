use serde::{Deserialize, Serialize};
use std::sync::{Mutex, OnceLock};
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter, Manager, PhysicalPosition, Position};

use crate::automation;
use crate::bridge::AppState;
use crate::hotkey;

struct AutoSelectionState {
    last_text: String,
    last_emit: Instant,
}

struct ModifierHotkeyState {
    shift_pressed_count: u8,
    shift_started_at: Option<Instant>,
    blocked: bool,
}

struct MouseSelectionState {
    left_pressed: bool,
    press_x: f64,
    press_y: f64,
    cursor_x: f64,
    cursor_y: f64,
    moved: bool,
    last_release_at: Option<Instant>,
    last_release_x: f64,
    last_release_y: f64,
}

static AUTO_SELECTION_STATE: OnceLock<Mutex<AutoSelectionState>> = OnceLock::new();
static PENDING_SELECTION_EVENT: OnceLock<Mutex<Option<SelectionEvent>>> = OnceLock::new();
static MODIFIER_HOTKEY_STATE: OnceLock<Mutex<ModifierHotkeyState>> = OnceLock::new();
static MOUSE_SELECTION_STATE: OnceLock<Mutex<MouseSelectionState>> = OnceLock::new();

const SHIFT_TRIGGER_MAX_HOLD_MS: u64 = 700;
const MOUSE_DRAG_MIN_DISTANCE_PX: f64 = 6.0;
const DOUBLE_CLICK_MAX_DISTANCE_PX: f64 = 14.0;
const DOUBLE_CLICK_MAX_INTERVAL_MS: u64 = 360;

fn auto_selection_state() -> &'static Mutex<AutoSelectionState> {
    AUTO_SELECTION_STATE.get_or_init(|| {
        Mutex::new(AutoSelectionState {
            last_text: String::new(),
            last_emit: Instant::now() - Duration::from_secs(5),
        })
    })
}

fn pending_selection_event() -> &'static Mutex<Option<SelectionEvent>> {
    PENDING_SELECTION_EVENT.get_or_init(|| Mutex::new(None))
}

fn modifier_hotkey_state() -> &'static Mutex<ModifierHotkeyState> {
    MODIFIER_HOTKEY_STATE.get_or_init(|| {
        Mutex::new(ModifierHotkeyState {
            shift_pressed_count: 0,
            shift_started_at: None,
            blocked: false,
        })
    })
}

fn mouse_selection_state() -> &'static Mutex<MouseSelectionState> {
    MOUSE_SELECTION_STATE.get_or_init(|| {
        Mutex::new(MouseSelectionState {
            left_pressed: false,
            press_x: 0.0,
            press_y: 0.0,
            cursor_x: 0.0,
            cursor_y: 0.0,
            moved: false,
            last_release_at: None,
            last_release_x: 0.0,
            last_release_y: 0.0,
        })
    })
}

fn pointer_distance(x1: f64, y1: f64, x2: f64, y2: f64) -> f64 {
    let dx = x1 - x2;
    let dy = y1 - y2;
    (dx * dx + dy * dy).sqrt()
}

fn should_trigger_auto_selection(event: &rdev::Event) -> bool {
    let Ok(mut guard) = mouse_selection_state().lock() else {
        return false;
    };

    match event.event_type {
        rdev::EventType::ButtonPress(rdev::Button::Left) => {
            guard.press_x = guard.cursor_x;
            guard.press_y = guard.cursor_y;
            guard.left_pressed = true;
            guard.moved = false;
            false
        }
        rdev::EventType::MouseMove { x, y } => {
            guard.cursor_x = x;
            guard.cursor_y = y;
            if !guard.left_pressed {
                return false;
            }

            if pointer_distance(guard.press_x, guard.press_y, x, y) >= MOUSE_DRAG_MIN_DISTANCE_PX {
                guard.moved = true;
            }
            false
        }
        rdev::EventType::ButtonRelease(rdev::Button::Left) => {
            let release_x = guard.cursor_x;
            let release_y = guard.cursor_y;

            let drag_distance =
                pointer_distance(guard.press_x, guard.press_y, release_x, release_y);
            let is_drag_selection =
                guard.left_pressed && (guard.moved || drag_distance >= MOUSE_DRAG_MIN_DISTANCE_PX);

            let now = Instant::now();
            let is_double_click = guard
                .last_release_at
                .map(|at| {
                    at.elapsed() <= Duration::from_millis(DOUBLE_CLICK_MAX_INTERVAL_MS)
                        && pointer_distance(
                            guard.last_release_x,
                            guard.last_release_y,
                            release_x,
                            release_y,
                        ) <= DOUBLE_CLICK_MAX_DISTANCE_PX
                })
                .unwrap_or(false);

            guard.left_pressed = false;
            guard.moved = false;
            guard.last_release_at = Some(now);
            guard.last_release_x = release_x;
            guard.last_release_y = release_y;

            is_drag_selection || is_double_click
        }
        _ => false,
    }
}

fn is_shift_key(key: rdev::Key) -> bool {
    matches!(key, rdev::Key::ShiftLeft | rdev::Key::ShiftRight)
}

fn on_modifier_hotkey_event(app: &AppHandle, event_type: &rdev::EventType) {
    match event_type {
        rdev::EventType::KeyPress(key) => {
            let Ok(mut guard) = modifier_hotkey_state().lock() else {
                return;
            };

            if is_shift_key(*key) {
                if guard.shift_pressed_count == 0 {
                    guard.shift_started_at = Some(Instant::now());
                    guard.blocked = false;
                }
                guard.shift_pressed_count = guard.shift_pressed_count.saturating_add(1).min(2);
                return;
            }

            if guard.shift_pressed_count > 0 {
                guard.blocked = true;
            }
        }
        rdev::EventType::KeyRelease(key) => {
            if !is_shift_key(*key) {
                return;
            }

            let should_trigger = {
                let Ok(mut guard) = modifier_hotkey_state().lock() else {
                    return;
                };

                if guard.shift_pressed_count == 0 {
                    return;
                }

                guard.shift_pressed_count = guard.shift_pressed_count.saturating_sub(1);
                if guard.shift_pressed_count > 0 {
                    return;
                }

                let quick_tap = guard
                    .shift_started_at
                    .map(|started| {
                        started.elapsed() <= Duration::from_millis(SHIFT_TRIGGER_MAX_HOLD_MS)
                    })
                    .unwrap_or(false);
                let allowed = quick_tap && !guard.blocked;

                guard.shift_started_at = None;
                guard.blocked = false;
                allowed
            };

            if should_trigger {
                let app_for_task = app.clone();
                tauri::async_runtime::spawn(async move {
                    let _ = hotkey::handle_modifier_shortcut(app_for_task).await;
                });
            }
        }
        _ => {}
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SelectionEvent {
    pub text: String,
    pub trigger: String,
}

pub fn take_pending_selection() -> Result<Option<SelectionEvent>, String> {
    let mut guard = pending_selection_event()
        .lock()
        .map_err(|_| "pending selection lock poisoned".to_owned())?;
    Ok(guard.take())
}

fn set_pending_selection(event: SelectionEvent) -> Result<(), String> {
    let mut guard = pending_selection_event()
        .lock()
        .map_err(|_| "pending selection lock poisoned".to_owned())?;
    *guard = Some(event);
    Ok(())
}

pub fn start_selection_listener(app: AppHandle) {
    std::thread::spawn(move || {
        let app_for_listener = app.clone();
        let callback = move |event: rdev::Event| {
            on_modifier_hotkey_event(&app_for_listener, &event.event_type);

            if should_trigger_auto_selection(&event) {
                let app_for_task = app_for_listener.clone();
                tauri::async_runtime::spawn(async move {
                    let _ = on_auto_selection(app_for_task).await;
                });
            }
        };

        if let Err(err) = rdev::listen(callback) {
            eprintln!("selection listener error: {err:?}");
        }
    });
}

pub(crate) fn is_any_app_window_focused(app: &AppHandle) -> bool {
    if let Some(main) = app.get_webview_window("main") {
        if main.is_focused().unwrap_or(false) {
            return true;
        }
    }
    if let Some(popover) = app.get_webview_window("popover") {
        if popover.is_focused().unwrap_or(false) {
            return true;
        }
    }
    if let Some(indicator) = app.get_webview_window("hotkey-indicator") {
        if indicator.is_focused().unwrap_or(false) {
            return true;
        }
    }
    false
}

async fn on_auto_selection(app: AppHandle) -> Result<(), String> {
    let state = app.state::<AppState>();
    let config = {
        let guard = state
            .config
            .lock()
            .map_err(|_| "config lock poisoned".to_owned())?;
        guard.clone()
    };
    if config.popover_trigger_mode != "auto" {
        return Ok(());
    }

    if is_any_app_window_focused(&app) {
        return Ok(());
    }

    let raw_text = tauri::async_runtime::spawn_blocking(automation::capture_selection_text)
        .await
        .map_err(|err| format!("capture selection task failed: {err}"))??;
    let selected = raw_text.replace('\r', "").trim().to_owned();
    if selected.is_empty() {
        let _ = hide_popover_window(&app);
        return Ok(());
    }

    {
        let mut guard = auto_selection_state()
            .lock()
            .map_err(|_| "auto selection state lock poisoned".to_owned())?;
        let repeated =
            guard.last_text == selected && guard.last_emit.elapsed() < Duration::from_millis(850);
        if repeated {
            return Ok(());
        }
        guard.last_text = selected.clone();
        guard.last_emit = Instant::now();
    }

    let cursor = tauri::async_runtime::spawn_blocking(automation::cursor_position)
        .await
        .map_err(|err| format!("capture cursor task failed: {err}"))?;

    show_popover_window(&app, selected, "auto".to_owned(), cursor)
}

pub fn show_popover_window(
    app: &AppHandle,
    text: String,
    trigger: String,
    cursor: Option<(i32, i32)>,
) -> Result<(), String> {
    set_pending_selection(SelectionEvent {
        text: text.clone(),
        trigger: trigger.clone(),
    })?;

    let popover = app
        .get_webview_window("popover")
        .ok_or_else(|| "popover window not found".to_owned())?;

    if let Some((x, y)) = cursor {
        let positioned = resolve_popover_position(app, &popover, x, y);
        popover
            .set_position(Position::Physical(positioned))
            .map_err(|err| format!("set popover position failed: {err}"))?;
    }

    popover
        .show()
        .map_err(|err| format!("show popover window failed: {err}"))?;
    std::thread::sleep(Duration::from_millis(40));
    emit_selection_changed(app, text, trigger)
}

fn resolve_popover_position(
    app: &AppHandle,
    popover: &tauri::WebviewWindow,
    cursor_x: i32,
    cursor_y: i32,
) -> PhysicalPosition<i32> {
    let mut left = cursor_x.max(0) + 18;
    let mut top = cursor_y.max(0) + 18;

    let Ok(window_size) = popover.outer_size() else {
        return PhysicalPosition::new(left, top);
    };

    let width = i32::try_from(window_size.width).unwrap_or(460);
    let height = i32::try_from(window_size.height).unwrap_or(320);

    let monitor = popover
        .current_monitor()
        .ok()
        .flatten()
        .or_else(|| app.primary_monitor().ok().flatten());

    let Some(monitor) = monitor else {
        return PhysicalPosition::new(left, top);
    };

    let margin = 12;
    let monitor_position = monitor.position();
    let monitor_size = monitor.size();

    let monitor_left = monitor_position.x;
    let monitor_top = monitor_position.y;
    let monitor_right = monitor_left + i32::try_from(monitor_size.width).unwrap_or(i32::MAX);
    let monitor_bottom = monitor_top + i32::try_from(monitor_size.height).unwrap_or(i32::MAX);

    let min_x = monitor_left + margin;
    let min_y = monitor_top + margin;
    let max_x = (monitor_right - width - margin).max(min_x);
    let max_y = (monitor_bottom - height - margin).max(min_y);

    left = left.clamp(min_x, max_x);
    top = top.clamp(min_y, max_y);

    PhysicalPosition::new(left, top)
}

pub fn hide_popover_window(app: &AppHandle) -> Result<(), String> {
    if let Some(popover) = app.get_webview_window("popover") {
        popover
            .hide()
            .map_err(|err| format!("hide popover window failed: {err}"))?;
    }
    Ok(())
}

pub fn emit_selection_changed(
    app: &AppHandle,
    text: String,
    trigger: String,
) -> Result<(), String> {
    let payload = SelectionEvent { text, trigger };
    app.emit("selection-changed", payload)
        .map_err(|err| format!("emit selection event failed: {err}"))
}
