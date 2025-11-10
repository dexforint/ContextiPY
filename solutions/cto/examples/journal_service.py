"""Background journal service and companion script.

This module demonstrates how to declare a service that runs in the
background and script endpoints that interact with it.

```requirements
tinydb>=4.8
```

The service uses TinyDB to persist journal entries. See the packaging and
build instructions in ``docs/advanced_topics.md#packaging`` for details on
bundling third-party libraries.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterator

from contextipy import Param, service, service_script
from contextipy.actions import Action, Notify, Text

_JOURNAL_PATH = Path.home() / ".contextipy-journal.json"


class JournalRepository:
    """Simple repository abstraction for journal persistence."""

    def __init__(self, path: Path) -> None:
        self._path = path
        from tinydb import TinyDB

        self._db = TinyDB(self._path)

    def add_entry(self, category: str, text: str) -> None:
        payload = {
            "category": category,
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._db.insert(payload)

    def all_entries(self) -> Iterator[dict[str, str]]:
        yield from self._db.all()


@service(
    service_id="daily_journal",
    title="Daily Journal Service",
    description="Persist lightweight journal entries in the background",
    icon="🗒️",
    categories=("examples", "service"),
)
def journal_service() -> JournalRepository:
    """Start the journal service and return a repository instance.

    Returns:
        An instance of :class:`JournalRepository` for use by service scripts.

    Notes:
        The service lifecycle is managed by :class:`contextipy.execution.service_manager.ServiceManager`.
        When the tray application exits, the manager gracefully shuts down the
        service and releases open file handles.
    """

    return JournalRepository(_JOURNAL_PATH)


@service_script(
    script_id="add_journal_entry",
    service_id="daily_journal",
    title="Add Journal Entry",
    description="Collect and persist a short journal entry",
)
def add_journal_entry(
    service_instance: JournalRepository,
    category: str = Param(default="general", description="Category for the entry"),
    text: str = Param(description="The note you want to remember"),
) -> list[Action]:
    """Persist a new journal entry via the running service.

    Args:
        service_instance: Resolved service instance managed by Contextipy.
        category: Categorisation label for the entry (defaults to ``general``).
        text: Content of the journal entry supplied by the user.

    Returns:
        A list containing textual confirmation and a desktop notification.
    """

    service_instance.add_entry(category=category, text=text)

    message = "Entry stored successfully"
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    body = f"[{timestamp}] ({category}) {text}"

    return [
        Text(content=body),
        Notify(title="Journal Updated", message=message),
    ]
