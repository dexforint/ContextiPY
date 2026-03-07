use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::net::{Shutdown, TcpStream};
use std::path::{Path, PathBuf};
use std::time::Duration;

use anyhow::{bail, Context, Result};

use crate::models::{AgentEndpoint, ResponseMessage, PROTOCOL_VERSION};

/// Возвращает путь к discovery-файлу агента.
///
/// По умолчанию это:
/// `~/.pcontext/runtime/agent-endpoint.json`
///
/// Для отладки можно переопределить путь через переменную окружения
/// `PCONTEXT_AGENT_ENDPOINT`.
pub fn resolve_agent_endpoint_path() -> Result<PathBuf> {
    if let Ok(custom_path) = std::env::var("PCONTEXT_AGENT_ENDPOINT") {
        let path = PathBuf::from(custom_path);
        return Ok(path);
    }

    let home_dir = dirs::home_dir().context("Не удалось определить домашнюю директорию пользователя.")?;

    Ok(home_dir
        .join(".pcontext")
        .join("runtime")
        .join("agent-endpoint.json"))
}

/// Читает и валидирует discovery-файл агента.
pub fn load_agent_endpoint(path: &Path) -> Result<AgentEndpoint> {
    let text = fs::read_to_string(path)
        .with_context(|| format!("Не удалось прочитать discovery-файл: {}", path.display()))?;

    let endpoint: AgentEndpoint = serde_json::from_str(&text)
        .with_context(|| format!("Некорректный JSON в discovery-файле: {}", path.display()))?;

    if endpoint.protocol_version != PROTOCOL_VERSION {
        bail!(
            "Несовместимая версия протокола: bridge ожидает {}, агент объявил {}.",
            PROTOCOL_VERSION,
            endpoint.protocol_version
        );
    }

    Ok(endpoint)
}

/// Отправляет JSON-запрос агенту и получает один JSON-ответ.
///
/// Протокол простой:
/// - одна JSON-строка на вход;
/// - одна JSON-строка на выход.
pub fn send_json_request<TRequest>(endpoint: &AgentEndpoint, request: &TRequest) -> Result<ResponseMessage>
where
    TRequest: serde::Serialize,
{
    let address = format!("{}:{}", endpoint.host, endpoint.port);

    let mut stream = TcpStream::connect(&address)
        .with_context(|| format!("Не удалось подключиться к агенту по адресу {address}."))?;

    stream
        .set_read_timeout(Some(Duration::from_secs(3)))
        .context("Не удалось установить timeout чтения для сокета.")?;

    stream
        .set_write_timeout(Some(Duration::from_secs(3)))
        .context("Не удалось установить timeout записи для сокета.")?;

    let payload =
        serde_json::to_vec(request).context("Не удалось сериализовать запрос в JSON.")?;

    stream
        .write_all(&payload)
        .context("Не удалось отправить тело запроса агенту.")?;

    stream
        .write_all(b"\n")
        .context("Не удалось отправить завершающий символ строки.")?;

    stream
        .flush()
        .context("Не удалось завершить отправку запроса агенту.")?;

    stream
        .shutdown(Shutdown::Write)
        .context("Не удалось завершить запись в сокет.")?;

    let mut reader = BufReader::new(stream);
    let mut response_line = String::new();

    let bytes_read = reader
        .read_line(&mut response_line)
        .context("Не удалось прочитать ответ агента.")?;

    if bytes_read == 0 {
        bail!("Агент закрыл соединение, не прислав ответ.");
    }

    let response: ResponseMessage =
        serde_json::from_str(&response_line).context("Ответ агента не является корректным JSON.")?;

    Ok(response)
}