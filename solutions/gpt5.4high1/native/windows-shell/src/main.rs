use std::path::PathBuf;

use anyhow::{Context, Result};
use clap::{Args, Parser, Subcommand};

use pcontext_bridge::bridge::{
    build_shell_context, get_endpoint, invoke_menu, list_services, ping, query_menu, reload_registry,
    response_to_compact_menu_lines, response_to_json, start_service, stop_service,
};
use pcontext_bridge::ipc::resolve_agent_endpoint_path;

#[derive(Debug, Parser)]
#[command(name = "pcontext-bridge")]
#[command(version = "0.1.0")]
#[command(about = "Rust bridge for PContext agent")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    PrintEndpointPath,
    ShowEndpoint,
    Ping,
    ReloadRegistry,
    ListServices,
    StartService(ServiceArgs),
    StopService(ServiceArgs),
    QueryMenu(ContextArgs),
    QueryMenuCompact(ContextArgs),
    InvokeMenu(InvokeArgs),
}

#[derive(Debug, Clone, Args)]
struct ContextArgs {
    #[arg(long, conflicts_with = "select")]
    background: Option<PathBuf>,

    #[arg(long, num_args = 1.., conflicts_with = "background")]
    select: Vec<PathBuf>,
}

#[derive(Debug, Clone, Args)]
struct InvokeArgs {
    menu_item_id: String,

    #[command(flatten)]
    context: ContextArgs,
}

#[derive(Debug, Clone, Args)]
struct ServiceArgs {
    service_id: String,
}

fn print_pretty_json(value: &serde_json::Value) -> Result<()> {
    let text = serde_json::to_string_pretty(value).context("Не удалось подготовить JSON к выводу.")?;
    println!("{text}");
    Ok(())
}

fn run() -> Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Command::PrintEndpointPath => {
            let endpoint_path = resolve_agent_endpoint_path()?;
            println!("{}", endpoint_path.display());
            Ok(())
        }

        Command::ShowEndpoint => {
            let endpoint = get_endpoint()?;
            let value =
                serde_json::to_value(endpoint).context("Не удалось сериализовать endpoint.")?;
            print_pretty_json(&value)
        }

        Command::Ping => {
            let response = ping()?;
            let value = response_to_json(&response);
            print_pretty_json(&value)
        }

        Command::ReloadRegistry => {
            let response = reload_registry()?;
            let value = response_to_json(&response);
            print_pretty_json(&value)
        }

        Command::ListServices => {
            let response = list_services()?;
            let value = response_to_json(&response);
            print_pretty_json(&value)
        }

        Command::StartService(service_args) => {
            let response = start_service(&service_args.service_id)?;
            let value = response_to_json(&response);
            print_pretty_json(&value)
        }

        Command::StopService(service_args) => {
            let response = stop_service(&service_args.service_id)?;
            let value = response_to_json(&response);
            print_pretty_json(&value)
        }

        Command::QueryMenu(context_args) => {
            let context = build_shell_context(context_args.background.as_deref(), &context_args.select)?;
            let response = query_menu(context)?;
            let value = response_to_json(&response);
            print_pretty_json(&value)
        }

        Command::QueryMenuCompact(context_args) => {
            let context = build_shell_context(context_args.background.as_deref(), &context_args.select)?;
            let response = query_menu(context)?;
            let lines = response_to_compact_menu_lines(&response)?;

            for line in lines {
                println!("{line}");
            }

            Ok(())
        }

        Command::InvokeMenu(invoke_args) => {
            let context =
                build_shell_context(invoke_args.context.background.as_deref(), &invoke_args.context.select)?;
            let response = invoke_menu(&invoke_args.menu_item_id, context)?;
            let value = response_to_json(&response);
            print_pretty_json(&value)
        }
    }
}

fn main() {
    if let Err(error) = run() {
        eprintln!("{error:#}");
        std::process::exit(1);
    }
}