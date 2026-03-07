use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};
use serde_json::{json, Value};

use crate::ipc::{load_agent_endpoint, resolve_agent_endpoint_path, send_json_request};
use crate::models::{
    AgentEndpoint, InvokeMenuItemRequest, ListServicesRequest, MenuItemDescriptor, PingRequest,
    QueryMenuRequest, ReloadRegistryRequest, ResponseMessage, ShellContext, ShellEntry,
    StartServiceRequest, StopServiceRequest, PROTOCOL_VERSION,
};

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
            current_folder: Some(path.to_string_lossy().into_owned()),
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
            current_folder = Some(parent.to_string_lossy().into_owned());
        }

        entries.push(ShellEntry {
            path: path.to_string_lossy().into_owned(),
            entry_type: entry_type.to_string(),
        });
    }

    Ok(ShellContext {
        source: "selection".to_string(),
        current_folder,
        entries,
    })
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