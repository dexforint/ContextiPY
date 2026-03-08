use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::process::Command;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use anyhow::{bail, Context, Result};
use serde_json::json;

use crate::ipc::{load_agent_endpoint, send_json_request_with_timeout};
use crate::models::{PingRequest, ResponseMessage, WindowsShellDevConfig, PROTOCOL_VERSION};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

pub fn runtime_dir() -> Result<PathBuf> {
    let home_dir = dirs::home_dir().context("Не удалось определить домашнюю директорию пользователя.")?;
    Ok(home_dir.join(".pcontext").join("runtime"))
}

pub fn launcher_log_path() -> Result<PathBuf> {
    Ok(runtime_dir()?.join("windows-launcher.log"))
}

pub fn shell_dev_config_path() -> Result<PathBuf> {
    Ok(runtime_dir()?.join("windows-shell-dev-config.json"))
}

pub fn append_launcher_log(level: &str, message: &str) {
    let result = (|| -> Result<()> {
        let log_path = launcher_log_path()?;
        if let Some(parent) = log_path.parent() {
            fs::create_dir_all(parent)
                .with_context(|| format!("Не удалось создать runtime-директорию: {}", parent.display()))?;
        }

        let timestamp = unix_timestamp_string();
        let line = format!("[{}] [{}] {}\n", timestamp, level, message);

        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&log_path)
            .with_context(|| format!("Не удалось открыть launcher log: {}", log_path.display()))?;

        file.write_all(line.as_bytes())
            .with_context(|| format!("Не удалось записать launcher log: {}", log_path.display()))?;

        Ok(())
    })();

    if result.is_err() {
    }
}

pub fn try_load_shell_dev_config() -> Result<Option<WindowsShellDevConfig>> {
    let config_path = shell_dev_config_path()?;
    if !config_path.is_file() {
        return Ok(None);
    }

    let text = read_json_text(&config_path)?;
    let config: WindowsShellDevConfig = serde_json::from_str(&text)
        .with_context(|| format!("Некорректный JSON в config-файле: {}", config_path.display()))?;

    Ok(Some(config))
}

pub fn load_shell_dev_config() -> Result<WindowsShellDevConfig> {
    try_load_shell_dev_config()?
        .context("Не найден windows-shell-dev-config.json. Выполни dev-регистрацию shell-скриптом.")
}

pub fn is_agent_available(timeout: Duration) -> Result<bool> {
    let endpoint_path = crate::ipc::resolve_agent_endpoint_path()?;
    if !endpoint_path.is_file() {
        return Ok(false);
    }

    let endpoint = load_agent_endpoint(&endpoint_path)?;
    let response = send_json_request_with_timeout(
        &endpoint,
        &PingRequest {
            kind: "ping",
            protocol_version: PROTOCOL_VERSION,
            token: endpoint.token.clone(),
        },
        timeout,
    )?;

    Ok(matches!(response, ResponseMessage::PingResult { .. }))
}

pub fn ensure_agent_available() -> Result<()> {
    if is_agent_available(Duration::from_secs(1)).unwrap_or(false) {
        append_launcher_log("INFO", "Агент уже доступен.");
        return Ok(());
    }

    let config = load_shell_dev_config()?;
    if !config.auto_start_gui_if_missing {
        bail!("GUI-агент не запущен, а автозапуск отключён в dev-config.");
    }

    append_launcher_log(
        "INFO",
        &format!(
            "Агент недоступен. Пытаемся запустить GUI: {} {:?}",
            config.gui_executable, config.gui_args
        ),
    );

    let mut command = Command::new(&config.gui_executable);
    command.args(&config.gui_args);

    if let Some(working_directory) = &config.working_directory {
        command.current_dir(working_directory);
    }

    #[cfg(windows)]
    {
        command.creation_flags(CREATE_NO_WINDOW);
    }

    command.spawn().with_context(|| {
        format!(
            "Не удалось запустить GUI-агент командой: {} {:?}",
            config.gui_executable, config.gui_args
        )
    })?;

    wait_for_agent(Duration::from_secs(20))
}

pub fn doctor_report() -> Result<serde_json::Value> {
    let endpoint_path = crate::ipc::resolve_agent_endpoint_path()?;
    let config_path = shell_dev_config_path()?;
    let log_path = launcher_log_path()?;

    let endpoint_exists = endpoint_path.is_file();
    let config_exists = config_path.is_file();
    let agent_available = is_agent_available(Duration::from_secs(1)).unwrap_or(false);
    let config = try_load_shell_dev_config()?;

    Ok(json!({
        "endpoint_path": endpoint_path,
        "endpoint_exists": endpoint_exists,
        "config_path": config_path,
        "config_exists": config_exists,
        "log_path": log_path,
        "agent_available": agent_available,
        "config": config,
    }))
}

fn wait_for_agent(timeout: Duration) -> Result<()> {
    let started_at = SystemTime::now();

    loop {
        if is_agent_available(Duration::from_secs(1)).unwrap_or(false) {
            append_launcher_log("INFO", "GUI-агент успешно стал доступен.");
            return Ok(());
        }

        let elapsed = SystemTime::now()
            .duration_since(started_at)
            .unwrap_or(Duration::from_secs(0));

        if elapsed >= timeout {
            bail!(
                "GUI-агент не стал доступен за {} секунд.",
                timeout.as_secs()
            );
        }

        std::thread::sleep(Duration::from_millis(500));
    }
}

fn read_json_text(path: &PathBuf) -> Result<String> {
    let raw_text = fs::read_to_string(path)
        .with_context(|| format!("Не удалось прочитать config-файл: {}", path.display()))?;

    Ok(strip_utf8_bom(&raw_text).to_string())
}

fn strip_utf8_bom(text: &str) -> &str {
    text.strip_prefix('\u{feff}').unwrap_or(text)
}

fn unix_timestamp_string() -> String {
    match SystemTime::now().duration_since(UNIX_EPOCH) {
        Ok(duration) => duration.as_secs().to_string(),
        Err(_) => "0".to_string(),
    }
}