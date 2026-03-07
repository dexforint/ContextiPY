use serde::{Deserialize, Serialize};

pub const PROTOCOL_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct AgentEndpoint {
    pub protocol_version: u32,
    pub host: String,
    pub port: u16,
    pub token: String,
    pub pid: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ShellEntry {
    pub path: String,
    pub entry_type: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ShellContext {
    pub source: String,
    pub current_folder: Option<String>,
    #[serde(default)]
    pub entries: Vec<ShellEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct MenuItemDescriptor {
    pub id: String,
    pub title: String,
    pub icon: Option<String>,
    pub enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ServiceDescriptor {
    pub service_id: String,
    pub title: String,
    pub running: bool,
    pub on_startup: bool,
    pub script_count: u32,
}

#[derive(Debug, Clone, Serialize)]
pub struct PingRequest {
    pub kind: &'static str,
    pub protocol_version: u32,
    pub token: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct QueryMenuRequest {
    pub kind: &'static str,
    pub protocol_version: u32,
    pub token: String,
    pub context: ShellContext,
}

#[derive(Debug, Clone, Serialize)]
pub struct InvokeMenuItemRequest {
    pub kind: &'static str,
    pub protocol_version: u32,
    pub token: String,
    pub menu_item_id: String,
    pub context: ShellContext,
}

#[derive(Debug, Clone, Serialize)]
pub struct ReloadRegistryRequest {
    pub kind: &'static str,
    pub protocol_version: u32,
    pub token: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct ListServicesRequest {
    pub kind: &'static str,
    pub protocol_version: u32,
    pub token: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct StartServiceRequest {
    pub kind: &'static str,
    pub protocol_version: u32,
    pub token: String,
    pub service_id: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct StopServiceRequest {
    pub kind: &'static str,
    pub protocol_version: u32,
    pub token: String,
    pub service_id: String,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "kind")]
pub enum ResponseMessage {
    #[serde(rename = "error")]
    Error {
        ok: bool,
        protocol_version: u32,
        error_code: String,
        message: String,
    },

    #[serde(rename = "ping_result")]
    PingResult {
        ok: bool,
        protocol_version: u32,
        pid: u32,
    },

    #[serde(rename = "query_menu_result")]
    QueryMenuResult {
        ok: bool,
        protocol_version: u32,
        items: Vec<MenuItemDescriptor>,
    },

    #[serde(rename = "invoke_menu_item_result")]
    InvokeMenuItemResult {
        ok: bool,
        protocol_version: u32,
        accepted: bool,
        message: String,
    },

    #[serde(rename = "reload_registry_result")]
    ReloadRegistryResult {
        ok: bool,
        protocol_version: u32,
        command_count: u32,
        service_count: u32,
        failure_count: u32,
    },

    #[serde(rename = "list_services_result")]
    ListServicesResult {
        ok: bool,
        protocol_version: u32,
        services: Vec<ServiceDescriptor>,
    },

    #[serde(rename = "start_service_result")]
    StartServiceResult {
        ok: bool,
        protocol_version: u32,
        service_id: String,
        accepted: bool,
        running: bool,
        message: String,
    },

    #[serde(rename = "stop_service_result")]
    StopServiceResult {
        ok: bool,
        protocol_version: u32,
        service_id: String,
        accepted: bool,
        running: bool,
        message: String,
    },
}