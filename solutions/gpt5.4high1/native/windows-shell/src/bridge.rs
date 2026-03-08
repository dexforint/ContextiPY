use std::path::{Path, PathBuf};
use std::time::Duration;

use anyhow::{bail, Context, Result};
use serde_json::{json, Value};

#[cfg(windows)]
use windows::core::PCWSTR;
#[cfg(windows)]
use windows::Win32::UI::WindowsAndMessaging::{MessageBoxW, MB_OK};

use crate::dev_support::{append_launcher_log, ensure_agent_available};
use crate::ipc::{
    load_agent_endpoint, resolve_agent_endpoint_path, send_json_request,
    send_json_request_with_timeout,
};
use crate::models::{
    AgentEndpoint, InvokeMenuItemRequest, ListServicesRequest, MenuItemDescriptor,
    OpenMenuChooserRequest, PingRequest, QueryMenuRequest, RecordLauncherEventRequest,
    ReloadRegistryRequest, ResponseMessage, ShellContext, ShellEntry, StartServiceRequest,
    StopServiceRequest, PROTOCOL_VERSION,
};

#[derive(Debug, Clone)]
pub enum SingleMatchExecution {
    Invoked(ResponseMessage),
    NoMatches(String),
    MultipleMatches(Vec<MenuItemDescriptor>),
}

pub fn detect_entry_type(path: &Path) -> Result<&'static str> {
    if path.is_dir() {
        return Ok("folder");
    }

    if path.is_file() {
        return Ok("file");
    }

    bail!("Путь не является ни файлом, ни папкой: {}", path.display())
}

pub fn build_shell_context(background: Option<&Path>, selected: &[PathBuf]) -> Result<ShellContext> {
    if let Some(background_folder) = background {
        let path = background_folder
            .canonicalize()
            .with_context(|| format!("Не удалось открыть путь: {}", background_folder.display()))?;

        if !path.is_dir() {
            bail!("Для background-контекста нужна папка: {}", path.display());
        }

        return Ok(ShellContext {
            source: "background".to_string(),
            current_folder: Some(normalize_path_for_shell(&path)),
            entries: Vec::new(),
        });
    }

    if selected.is_empty() {
        bail!("Нужно передать либо background-папку, либо хотя бы один выбранный путь.");
    }

    let mut entries = Vec::new();
    let mut current_folder: Option<String> = None;

    for raw_path in selected {
        let path = raw_path
            .canonicalize()
            .with_context(|| format!("Не удалось открыть путь: {}", raw_path.display()))?;

        let entry_type = detect_entry_type(&path)?;

        if current_folder.is_none() {
            let parent = path
                .parent()
                .context("Не удалось определить родительскую папку выбранного объекта.")?;
            current_folder = Some(normalize_path_for_shell(parent));
        }

        entries.push(ShellEntry {
            path: normalize_path_for_shell(&path),
            entry_type: entry_type.to_string(),
        });
    }

    Ok(ShellContext {
        source: "selection".to_string(),
        current_folder,
        entries,
    })
}

pub fn build_single_selection_context(selected_path: &Path) -> Result<ShellContext> {
    build_shell_context(None, &[selected_path.to_path_buf()])
}

pub fn get_endpoint() -> Result<AgentEndpoint> {
    let endpoint_path = resolve_agent_endpoint_path()?;
    load_agent_endpoint(&endpoint_path)
}

pub fn ping() -> Result<ResponseMessage> {
    let endpoint = get_endpoint()?;
    send_json_request(
        &endpoint,
        &PingRequest {
            kind: "ping",
            protocol_version: PROTOCOL_VERSION,
            token: endpoint.token.clone(),
        },
    )
}

pub fn reload_registry() -> Result<ResponseMessage> {
    let endpoint = get_endpoint()?;
    send_json_request(
        &endpoint,
        &ReloadRegistryRequest {
            kind: "reload_registry",
            protocol_version: PROTOCOL_VERSION,
            token: endpoint.token.clone(),
        },
    )
}

pub fn list_services() -> Result<ResponseMessage> {
    let endpoint = get_endpoint()?;
    send_json_request(
        &endpoint,
        &ListServicesRequest {
            kind: "list_services",
            protocol_version: PROTOCOL_VERSION,
            token: endpoint.token.clone(),
        },
    )
}

pub fn start_service(service_id: &str) -> Result<ResponseMessage> {
    let endpoint = get_endpoint()?;
    send_json_request(
        &endpoint,
        &StartServiceRequest {
            kind: "start_service",
            protocol_version: PROTOCOL_VERSION,
            token: endpoint.token.clone(),
            service_id: service_id.to_string(),
        },
    )
}

pub fn stop_service(service_id: &str) -> Result<ResponseMessage> {
    let endpoint = get_endpoint()?;
    send_json_request(
        &endpoint,
        &StopServiceRequest {
            kind: "stop_service",
            protocol_version: PROTOCOL_VERSION,
            token: endpoint.token.clone(),
            service_id: service_id.to_string(),
        },
    )
}

pub fn query_menu(context: ShellContext) -> Result<ResponseMessage> {
    let endpoint = get_endpoint()?;
    send_json_request(
        &endpoint,
        &QueryMenuRequest {
            kind: "query_menu",
            protocol_version: PROTOCOL_VERSION,
            token: endpoint.token.clone(),
            context,
        },
    )
}

pub fn invoke_menu(menu_item_id: &str, context: ShellContext) -> Result<ResponseMessage> {
    let endpoint = get_endpoint()?;
    send_json_request(
        &endpoint,
        &InvokeMenuItemRequest {
            kind: "invoke_menu_item",
            protocol_version: PROTOCOL_VERSION,
            token: endpoint.token.clone(),
            menu_item_id: menu_item_id.to_string(),
            context,
        },
    )
}

pub fn open_menu_chooser(context: ShellContext) -> Result<ResponseMessage> {
    ensure_agent_available()?;

    let endpoint = get_endpoint()?;
    send_json_request_with_timeout(
        &endpoint,
        &OpenMenuChooserRequest {
            kind: "open_menu_chooser",
            protocol_version: PROTOCOL_VERSION,
            token: endpoint.token.clone(),
            context,
        },
        Duration::from_secs(3600),
    )
}

pub fn record_launcher_event(
    event_id: &str,
    title: &str,
    message: &str,
    success: bool,
    context: Option<ShellContext>,
) -> Result<ResponseMessage> {
    let endpoint = get_endpoint()?;
    send_json_request(
        &endpoint,
        &RecordLauncherEventRequest {
            kind: "record_launcher_event",
            protocol_version: PROTOCOL_VERSION,
            token: endpoint.token.clone(),
            event_id: event_id.to_string(),
            title: title.to_string(),
            message: message.to_string(),
            success,
            context,
        },
    )
}

pub fn run_single_match(context: ShellContext) -> Result<SingleMatchExecution> {
    ensure_agent_available()?;

    let query_response = query_menu(context.clone())?;
    match query_response {
        ResponseMessage::QueryMenuResult { items, .. } => {
            let enabled_items: Vec<MenuItemDescriptor> =
                items.into_iter().filter(|item| item.enabled).collect();

            match enabled_items.len() {
                0 => Ok(SingleMatchExecution::NoMatches(
                    "Подходящие команды не найдены.".to_string(),
                )),
                1 => {
                    let selected_id = enabled_items[0].id.clone();
                    let invoke_response = invoke_menu(&selected_id, context)?;
                    Ok(SingleMatchExecution::Invoked(invoke_response))
                }
                _ => Ok(SingleMatchExecution::MultipleMatches(enabled_items)),
            }
        }
        ResponseMessage::Error {
            error_code,
            message,
            ..
        } => bail!("Агент вернул ошибку при query_menu: {error_code}: {message}"),
        other => bail!("Агент вернул неожиданный ответ при query_menu: {:?}", other),
    }
}

pub fn background_native_test(background_folder: &Path) -> Result<()> {
    let context = build_shell_context(Some(background_folder), &[])?;
    let current_folder = context
        .current_folder
        .clone()
        .unwrap_or_else(|| background_folder.display().to_string());

    let agent_status = format_agent_status();

    let message = format!(
        "PContext safe background command executed.\n\nCurrent folder:\n{}\n\n{}",
        current_folder, agent_status
    );

    append_launcher_log(
        "INFO",
        &format!("background-native-test for '{}'", current_folder),
    );

    show_message_box("PContext Dev", &message)
}

pub fn background_show_menu(background_folder: &Path) -> Result<ResponseMessage> {
    let context = build_shell_context(Some(background_folder), &[])?;
    append_launcher_log(
        "INFO",
        &format!(
            "background-show-menu requested for '{}'",
            context.current_folder.clone().unwrap_or_default()
        ),
    );
    open_menu_chooser(context)
}

pub fn background_run_single_match(background_folder: &Path) -> Result<SingleMatchExecution> {
    let context = build_shell_context(Some(background_folder), &[])?;
    append_launcher_log(
        "INFO",
        &format!(
            "background-run-single-match requested for '{}'",
            context.current_folder.clone().unwrap_or_default()
        ),
    );
    run_single_match(context)
}

pub fn selection_native_test(selected_path: &Path) -> Result<()> {
    let context = build_single_selection_context(selected_path)?;
    let selected_entry = context
        .entries
        .first()
        .context("Не удалось определить выбранный объект.")?;

    let agent_status = format_agent_status();

    let message = format!(
        "PContext safe selection command executed.\n\nSelected path:\n{}\n\nType: {}\n\n{}",
        selected_entry.path, selected_entry.entry_type, agent_status
    );

    append_launcher_log(
        "INFO",
        &format!(
            "selection-native-test for '{}' ({})",
            selected_entry.path, selected_entry.entry_type
        ),
    );

    show_message_box("PContext Dev", &message)
}

pub fn selection_show_menu(selected_path: &Path) -> Result<ResponseMessage> {
    let context = build_single_selection_context(selected_path)?;
    let selected_entry = context
        .entries
        .first()
        .context("Не удалось определить выбранный объект.")?;

    append_launcher_log(
        "INFO",
        &format!(
            "selection-show-menu requested for '{}' ({})",
            selected_entry.path, selected_entry.entry_type
        ),
    );

    open_menu_chooser(context)
}

pub fn selection_run_single_match(selected_path: &Path) -> Result<SingleMatchExecution> {
    let context = build_single_selection_context(selected_path)?;
    let selected_entry = context
        .entries
        .first()
        .context("Не удалось определить выбранный объект.")?;

    append_launcher_log(
        "INFO",
        &format!(
            "selection-run-single-match requested for '{}' ({})",
            selected_entry.path, selected_entry.entry_type
        ),
    );

    run_single_match(context)
}

fn format_agent_status() -> String {
    match ping() {
        Ok(ResponseMessage::PingResult { pid, .. }) => {
            format!("Агент доступен. PID: {pid}")
        }
        Ok(ResponseMessage::Error {
            error_code,
            message,
            ..
        }) => {
            format!("Агент ответил ошибкой: {error_code}: {message}")
        }
        Ok(_) => {
            "Агент ответил неожиданным сообщением.".to_string()
        }
        Err(error) => {
            format!("Агент недоступен: {error}")
        }
    }
}

#[cfg(windows)]
fn show_message_box(title: &str, text: &str) -> Result<()> {
    let title_wide = to_wide_null(title);
    let text_wide = to_wide_null(text);

    unsafe {
        MessageBoxW(
            None,
            PCWSTR(text_wide.as_ptr()),
            PCWSTR(title_wide.as_ptr()),
            MB_OK,
        );
    }

    Ok(())
}

#[cfg(not(windows))]
fn show_message_box(_title: &str, _text: &str) -> Result<()> {
    bail!("Эта команда поддерживается только на Windows.")
}

fn to_wide_null(value: &str) -> Vec<u16> {
    value.encode_utf16().chain(std::iter::once(0)).collect()
}

fn normalize_path_for_shell(path: &Path) -> String {
    let raw = path.display().to_string();

    #[cfg(windows)]
    {
        if let Some(stripped) = raw.strip_prefix(r"\\?\UNC\") {
            return format!(r"\\{}", stripped);
        }

        if let Some(stripped) = raw.strip_prefix(r"\\?\") {
            return stripped.to_string();
        }
    }

    raw
}

pub fn response_to_json(response: &ResponseMessage) -> Value {
    match response {
        ResponseMessage::Error {
            ok,
            protocol_version,
            error_code,
            message,
        } => json!({
            "kind": "error",
            "ok": ok,
            "protocol_version": protocol_version,
            "error_code": error_code,
            "message": message,
        }),

        ResponseMessage::PingResult {
            ok,
            protocol_version,
            pid,
        } => json!({
            "kind": "ping_result",
            "ok": ok,
            "protocol_version": protocol_version,
            "pid": pid,
        }),

        ResponseMessage::QueryMenuResult {
            ok,
            protocol_version,
            items,
        } => json!({
            "kind": "query_menu_result",
            "ok": ok,
            "protocol_version": protocol_version,
            "items": items,
        }),

        ResponseMessage::InvokeMenuItemResult {
            ok,
            protocol_version,
            accepted,
            message,
        } => json!({
            "kind": "invoke_menu_item_result",
            "ok": ok,
            "protocol_version": protocol_version,
            "accepted": accepted,
            "message": message,
        }),

        ResponseMessage::ReloadRegistryResult {
            ok,
            protocol_version,
            command_count,
            service_count,
            failure_count,
        } => json!({
            "kind": "reload_registry_result",
            "ok": ok,
            "protocol_version": protocol_version,
            "command_count": command_count,
            "service_count": service_count,
            "failure_count": failure_count,
        }),

        ResponseMessage::ListServicesResult {
            ok,
            protocol_version,
            services,
        } => json!({
            "kind": "list_services_result",
            "ok": ok,
            "protocol_version": protocol_version,
            "services": services,
        }),

        ResponseMessage::StartServiceResult {
            ok,
            protocol_version,
            service_id,
            accepted,
            running,
            message,
        } => json!({
            "kind": "start_service_result",
            "ok": ok,
            "protocol_version": protocol_version,
            "service_id": service_id,
            "accepted": accepted,
            "running": running,
            "message": message,
        }),

        ResponseMessage::StopServiceResult {
            ok,
            protocol_version,
            service_id,
            accepted,
            running,
            message,
        } => json!({
            "kind": "stop_service_result",
            "ok": ok,
            "protocol_version": protocol_version,
            "service_id": service_id,
            "accepted": accepted,
            "running": running,
            "message": message,
        }),

        ResponseMessage::OpenMenuChooserResult {
            ok,
            protocol_version,
            cancelled,
            accepted,
            message,
        } => json!({
            "kind": "open_menu_chooser_result",
            "ok": ok,
            "protocol_version": protocol_version,
            "cancelled": cancelled,
            "accepted": accepted,
            "message": message,
        }),

        ResponseMessage::RecordLauncherEventResult {
            ok,
            protocol_version,
            recorded,
        } => json!({
            "kind": "record_launcher_event_result",
            "ok": ok,
            "protocol_version": protocol_version,
            "recorded": recorded,
        }),
    }
}

pub fn response_to_compact_menu_lines(response: &ResponseMessage) -> Result<Vec<String>> {
    match response {
        ResponseMessage::QueryMenuResult { items, .. } => serialize_menu_items(items),
        ResponseMessage::Error {
            error_code,
            message,
            ..
        } => bail!("Агент вернул ошибку: {error_code}: {message}"),
        _ => bail!("Ожидался ответ типа query_menu_result."),
    }
}

fn serialize_menu_items(items: &[MenuItemDescriptor]) -> Result<Vec<String>> {
    items.iter()
        .map(|item| serde_json::to_string(item).context("Не удалось сериализовать пункт меню."))
        .collect()
}