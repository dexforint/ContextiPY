"""Interactive script demonstrating the Ask dialog system.

This example shows how to use Contextipy's question-based dialog system
to collect structured user input before executing script logic.

The Ask() function renders a UI dialog with fields defined by a Questions
dataclass, validates the inputs, and returns typed responses.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from contextipy import Folder, Param, oneshot_script
from contextipy.actions import Action, Notify, Open, Text
from contextipy.questions import Ask, Question, Questions


@dataclass
class BackupConfiguration(Questions):
    """Questions asking for backup configuration details."""

    source_folder: Annotated[Path, Question.path(title="Source Folder", required=True)]
    destination_folder: Annotated[Path, Question.path(title="Destination Folder", required=True)]
    compress: Annotated[bool, Question.boolean(title="Compress Archive", default=False)]
    include_hidden: Annotated[
        bool,
        Question.boolean(
            title="Include Hidden Files",
            description="Copy hidden files and folders starting with '.'",
            default=False,
        ),
    ]
    retention_days: Annotated[
        int | None,
        Question.integer(
            title="Retention Days",
            description="Delete old backups after this many days (optional)",
            ge=1,
            le=365,
            required=False,
        ),
    ]


@oneshot_script(
    script_id="backup_wizard",
    title="Backup Wizard",
    description="Configure and execute a backup operation",
    accepts=[Folder],
    icon="💾",
    categories=["examples", "dialog", "backup"],
)
def backup_wizard(
    selected_paths: list[Path] | None = None,
    dry_run: bool = Param(default=False, description="Show what would be backed up without copying"),
) -> list[Action]:
    """Collect backup configuration and execute the backup.

    This script demonstrates the Ask dialog for collecting structured input.
    When the user clicks the script in the Contextipy tray menu, a dialog
    is shown with fields defined by the BackupConfiguration dataclass.

    Args:
        selected_paths: Optionally pre-selected folders via context menu
        dry_run: If True, simulate the backup without copying files

    Returns:
        Actions showing backup results or cancellation message.
    """
    config = Ask(BackupConfiguration)

    if config is None:
        return [
            Notify(title="Cancelled", message="Backup wizard was cancelled"),
            Text(content="User cancelled the backup configuration dialog."),
        ]

    source = config.source_folder
    destination = config.destination_folder

    if not source.exists() or not source.is_dir():
        return [
            Notify(title="Error", message=f"Source folder does not exist: {source}"),
            Text(content=f"❌ Invalid source: {source}"),
        ]

    if not destination.exists():
        try:
            destination.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return [
                Notify(title="Error", message=f"Could not create destination: {e}"),
                Text(content=f"❌ Failed to create destination: {destination}"),
            ]

    mode = "🚫 DRY RUN" if dry_run else "✅ ACTIVE"
    compression = "🗜️ Compressed" if config.compress else "📂 Uncompressed"

    report = f"{mode} Backup Configuration:\n\n"
    report += f"Source: {source}\n"
    report += f"Destination: {destination}\n"
    report += f"Compression: {compression}\n"
    report += f"Include Hidden: {'Yes' if config.include_hidden else 'No'}\n"
    if config.retention_days is not None:
        report += f"Retention: {config.retention_days} days\n"
    else:
        report += "Retention: Unlimited\n"

    if not dry_run:
        report += "\n🔄 Backup would execute here in a real implementation.\n"
    else:
        report += "\n🚫 Dry run - no files were copied.\n"

    return [
        Notify(title="Backup Complete" if not dry_run else "Dry Run Complete"),
        Text(content=report),
        Open(target=destination),
    ]
