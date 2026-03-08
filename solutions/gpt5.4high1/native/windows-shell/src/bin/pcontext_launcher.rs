#![cfg_attr(windows, windows_subsystem = "windows")]

use std::path::PathBuf;

use anyhow::{Context, Result};
use clap::{Args, Parser, Subcommand};

use pcontext_native::bridge::{
    background_native_test, background_run_single_match, background_show_menu, build_shell_context,
    build_single_selection_context, record_launcher_event, selection_native_test,
    selection_run_single_match, selection_show_menu, SingleMatchExecution,
};
use pcontext_native::dev_support::append_launcher_log;
use pcontext_native::models::{ResponseMessage, ShellContext};

#[cfg(windows)]
use windows::core::PCWSTR;
#[cfg(windows)]
use windows::Win32::UI::WindowsAndMessaging::{MessageBoxW, MB_ICONERROR, MB_OK};

#[derive(Debug, Parser)]
#[command(name = "pcontext-launcher")]
#[command(version = "0.1.0")]
#[command(about = "PContext hidden launcher for Windows shell commands")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    BackgroundNativeTest(BackgroundArgs),
    BackgroundShowMenu(BackgroundArgs),
    BackgroundRunSingleMatch(BackgroundArgs),
    SelectionNativeTest(SelectionArgs),
    SelectionShowMenu(SelectionArgs),
    SelectionRunSingleMatch(SelectionArgs),
}

#[derive(Debug, Clone, Args)]
struct BackgroundArgs {
    #[arg(long)]
    background: PathBuf,
}

#[derive(Debug, Clone, Args)]
struct SelectionArgs {
    #[arg(long)]
    path: PathBuf,
}

fn run() -> Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Command::BackgroundNativeTest(args) => {
            append_launcher_log(
                "INFO",
                &format!("Launcher command: background-native-test '{}'", args.background.display()),
            );

            let context = build_shell_context(Some(&args.background), &[]).ok();
            let result = background_native_test(&args.background)
                .with_context(|| format!("Не удалось выполнить background-native-test для '{}'", args.background.display()));

            record_launcher_event_best_effort(
                "windows_launcher.background_native_test",
                "Windows launcher: background native test",
                result_message(&result),
                result.is_ok(),
                context,
            );

            result
        }
        Command::BackgroundShowMenu(args) => {
            append_launcher_log(
                "INFO",
                &format!("Launcher command: background-show-menu '{}'", args.background.display()),
            );

            let context = build_shell_context(Some(&args.background), &[]).ok();
            match background_show_menu(&args.background)
                .with_context(|| format!("Не удалось выполнить background-show-menu для '{}'", args.background.display()))
            {
                Ok(response) => handle_chooser_response(
                    response,
                    "windows_launcher.background_show_menu",
                    "Windows launcher: background show menu",
                    context,
                ),
                Err(error) => {
                    record_launcher_event_best_effort(
                        "windows_launcher.background_show_menu",
                        "Windows launcher: background show menu",
                        &format!("{error:#}"),
                        false,
                        context,
                    );
                    Err(error)
                }
            }
        }
        Command::BackgroundRunSingleMatch(args) => {
            append_launcher_log(
                "INFO",
                &format!("Launcher command: background-run-single-match '{}'", args.background.display()),
            );

            let context = build_shell_context(Some(&args.background), &[]).ok();
            match background_run_single_match(&args.background)
                .with_context(|| format!("Не удалось выполнить background-run-single-match для '{}'", args.background.display()))
            {
                Ok(result) => handle_single_match_result(
                    result,
                    "windows_launcher.background_run_single_match",
                    "Windows launcher: background run single match",
                    context,
                ),
                Err(error) => {
                    record_launcher_event_best_effort(
                        "windows_launcher.background_run_single_match",
                        "Windows launcher: background run single match",
                        &format!("{error:#}"),
                        false,
                        context,
                    );
                    Err(error)
                }
            }
        }
        Command::SelectionNativeTest(args) => {
            append_launcher_log(
                "INFO",
                &format!("Launcher command: selection-native-test '{}'", args.path.display()),
            );

            let context = build_single_selection_context(&args.path).ok();
            let result = selection_native_test(&args.path)
                .with_context(|| format!("Не удалось выполнить selection-native-test для '{}'", args.path.display()));

            record_launcher_event_best_effort(
                "windows_launcher.selection_native_test",
                "Windows launcher: selection native test",
                result_message(&result),
                result.is_ok(),
                context,
            );

            result
        }
        Command::SelectionShowMenu(args) => {
            append_launcher_log(
                "INFO",
                &format!("Launcher command: selection-show-menu '{}'", args.path.display()),
            );

            let context = build_single_selection_context(&args.path).ok();
            match selection_show_menu(&args.path)
                .with_context(|| format!("Не удалось выполнить selection-show-menu для '{}'", args.path.display()))
            {
                Ok(response) => handle_chooser_response(
                    response,
                    "windows_launcher.selection_show_menu",
                    "Windows launcher: selection show menu",
                    context,
                ),
                Err(error) => {
                    record_launcher_event_best_effort(
                        "windows_launcher.selection_show_menu",
                        "Windows launcher: selection show menu",
                        &format!("{error:#}"),
                        false,
                        context,
                    );
                    Err(error)
                }
            }
        }
        Command::SelectionRunSingleMatch(args) => {
            append_launcher_log(
                "INFO",
                &format!("Launcher command: selection-run-single-match '{}'", args.path.display()),
            );

            let context = build_single_selection_context(&args.path).ok();
            match selection_run_single_match(&args.path)
                .with_context(|| format!("Не удалось выполнить selection-run-single-match для '{}'", args.path.display()))
            {
                Ok(result) => handle_single_match_result(
                    result,
                    "windows_launcher.selection_run_single_match",
                    "Windows launcher: selection run single match",
                    context,
                ),
                Err(error) => {
                    record_launcher_event_best_effort(
                        "windows_launcher.selection_run_single_match",
                        "Windows launcher: selection run single match",
                        &format!("{error:#}"),
                        false,
                        context,
                    );
                    Err(error)
                }
            }
        }
    }
}

fn handle_chooser_response(
    response: ResponseMessage,
    event_id: &str,
    title: &str,
    context: Option<ShellContext>,
) -> Result<()> {
    match response {
        ResponseMessage::OpenMenuChooserResult {
            cancelled,
            accepted,
            message,
            ..
        } => {
            append_launcher_log(
                "INFO",
                &format!(
                    "Chooser result: cancelled={}, accepted={}, message={}",
                    cancelled, accepted, message
                ),
            );

            record_launcher_event_best_effort(
                event_id,
                title,
                &message,
                accepted || cancelled,
                context,
            );

            if cancelled || accepted {
                return Ok(());
            }

            show_info_message("PContext", &message);
            Ok(())
        }
        ResponseMessage::Error {
            error_code,
            message,
            ..
        } => {
            let full_message = format!("{error_code}: {message}");
            append_launcher_log("ERROR", &format!("Agent returned error: {}", full_message));

            record_launcher_event_best_effort(
                event_id,
                title,
                &full_message,
                false,
                context,
            );

            show_error_message("PContext Launcher Error", &full_message);
            Ok(())
        }
        other => {
            let full_message = format!("Неожиданный ответ агента: {:?}", other);
            append_launcher_log("ERROR", &full_message);

            record_launcher_event_best_effort(
                event_id,
                title,
                &full_message,
                false,
                context,
            );

            show_error_message("PContext Launcher Error", &full_message);
            Ok(())
        }
    }
}

fn handle_single_match_result(
    result: SingleMatchExecution,
    event_id: &str,
    title: &str,
    context: Option<ShellContext>,
) -> Result<()> {
    match result {
        SingleMatchExecution::Invoked(response) => match response {
            ResponseMessage::InvokeMenuItemResult {
                accepted,
                message,
                ..
            } => {
                append_launcher_log(
                    "INFO",
                    &format!("Single-match invoke result: accepted={}, message={}", accepted, message),
                );

                record_launcher_event_best_effort(
                    event_id,
                    title,
                    &message,
                    accepted,
                    context,
                );

                if accepted {
                    return Ok(());
                }

                show_info_message("PContext", &message);
                Ok(())
            }
            ResponseMessage::Error {
                error_code,
                message,
                ..
            } => {
                let full_message = format!("{error_code}: {message}");
                append_launcher_log("ERROR", &full_message);

                record_launcher_event_best_effort(
                    event_id,
                    title,
                    &full_message,
                    false,
                    context,
                );

                show_error_message("PContext Launcher Error", &full_message);
                Ok(())
            }
            other => {
                let full_message = format!("Неожиданный ответ invoke: {:?}", other);
                append_launcher_log("ERROR", &full_message);

                record_launcher_event_best_effort(
                    event_id,
                    title,
                    &full_message,
                    false,
                    context,
                );

                show_error_message("PContext Launcher Error", &full_message);
                Ok(())
            }
        },
        SingleMatchExecution::NoMatches(message) => {
            append_launcher_log("INFO", &format!("Single-match: {}", message));

            record_launcher_event_best_effort(
                event_id,
                title,
                &message,
                false,
                context,
            );

            show_info_message("PContext", &message);
            Ok(())
        }
        SingleMatchExecution::MultipleMatches(items) => {
            let items_text = items
                .iter()
                .map(|item| format!("• {}", item.title))
                .collect::<Vec<String>>()
                .join("\n");

            let full_message = format!(
                "Найдено несколько подходящих команд:\n\n{}\n\nИспользуй пункт 'Show matching scripts'.",
                items_text
            );

            append_launcher_log("INFO", &full_message);

            record_launcher_event_best_effort(
                event_id,
                title,
                &full_message,
                false,
                context,
            );

            show_info_message("PContext", &full_message);
            Ok(())
        }
    }
}

fn record_launcher_event_best_effort(
    event_id: &str,
    title: &str,
    message: &str,
    success: bool,
    context: Option<ShellContext>,
) {
    if let Err(error) = record_launcher_event(event_id, title, message, success, context) {
        append_launcher_log(
            "WARN",
            &format!("Не удалось записать launcher-событие в агент: {error:#}"),
        );
    }
}

fn result_message(result: &Result<()>) -> &str {
    if result.is_ok() {
        "Команда launcher выполнена успешно."
    } else {
        "Команда launcher завершилась ошибкой."
    }
}

fn main() {
    if let Err(error) = run() {
        append_launcher_log("ERROR", &format!("{error:#}"));
        show_error_message("PContext Launcher Error", &format!("{error:#}"));
        std::process::exit(1);
    }
}

#[cfg(windows)]
fn show_error_message(title: &str, text: &str) {
    let title_wide = to_wide_null(title);
    let text_wide = to_wide_null(text);

    unsafe {
        let _ = MessageBoxW(
            None,
            PCWSTR(text_wide.as_ptr()),
            PCWSTR(title_wide.as_ptr()),
            MB_OK | MB_ICONERROR,
        );
    }
}

#[cfg(not(windows))]
fn show_error_message(_title: &str, _text: &str) {}

#[cfg(windows)]
fn show_info_message(title: &str, text: &str) {
    let title_wide = to_wide_null(title);
    let text_wide = to_wide_null(text);

    unsafe {
        let _ = MessageBoxW(
            None,
            PCWSTR(text_wide.as_ptr()),
            PCWSTR(title_wide.as_ptr()),
            MB_OK,
        );
    }
}

#[cfg(not(windows))]
fn show_info_message(_title: &str, _text: &str) {}

fn to_wide_null(value: &str) -> Vec<u16> {
    value.encode_utf16().chain(std::iter::once(0)).collect()
}