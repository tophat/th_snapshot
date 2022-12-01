from collections import defaultdict
from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    DefaultDict,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
)

import pytest

from .constants import EXIT_STATUS_FAIL_UNUSED
from .data import SnapshotCollections
from .report import SnapshotReport
from .types import (
    SerializedData,
    SnapshotIndex,
)

if TYPE_CHECKING:
    from .assertion import SnapshotAssertion
    from .extensions.base import AbstractSyrupyExtension


@dataclass
class SnapshotSession:
    # pytest.Session
    pytest_session: Any
    # Snapshot report generated on finish
    report: Optional["SnapshotReport"] = None
    # All the collected test items
    _collected_items: Set["pytest.Item"] = field(default_factory=set)
    # All the selected test items. Will be set to False until the test item is run.
    _selected_items: Dict[str, bool] = field(default_factory=dict)
    _assertions: List["SnapshotAssertion"] = field(default_factory=list)
    _extensions: Dict[str, "AbstractSyrupyExtension"] = field(default_factory=dict)

    _locations_discovered: DefaultDict[str, Set[Any]] = field(
        default_factory=lambda: defaultdict(set)
    )

    _queued_snapshot_writes: Dict[
        "AbstractSyrupyExtension", List[Tuple["SerializedData", "SnapshotIndex"]]
    ] = field(default_factory=dict)

    def queue_snapshot_write(
        self,
        extension: "AbstractSyrupyExtension",
        data: "SerializedData",
        index: "SnapshotIndex",
    ) -> None:
        queue = self._queued_snapshot_writes.get(extension, [])
        queue.append((data, index))
        self._queued_snapshot_writes[extension] = queue

    def flush_snapshot_write_queue(self) -> None:
        for extension, queued_write in self._queued_snapshot_writes.items():
            if queued_write:
                extension.write_snapshot_batch(snapshots=queued_write)
        self._queued_snapshot_writes = {}

    @property
    def update_snapshots(self) -> bool:
        return bool(self.pytest_session.config.option.update_snapshots)

    @property
    def warn_unused_snapshots(self) -> bool:
        return bool(self.pytest_session.config.option.warn_unused_snapshots)

    def collect_items(self, items: List["pytest.Item"]) -> None:
        self._collected_items.update(self.filter_valid_items(items))

    def select_items(self, items: List["pytest.Item"]) -> None:
        for item in self.filter_valid_items(items):
            self._selected_items[getattr(item, "nodeid")] = False  # noqa: B009

    def start(self) -> None:
        self.report = None
        self._collected_items = set()
        self._selected_items = {}
        self._assertions = []
        self._extensions = {}
        self._locations_discovered = defaultdict(set)

    def ran_item(self, nodeid: str) -> None:
        if nodeid in self._selected_items:
            self._selected_items[nodeid] = True

    def finish(self) -> int:
        exitstatus = 0
        self.flush_snapshot_write_queue()
        self.report = SnapshotReport(
            base_dir=self.pytest_session.config.rootdir,
            collected_items=self._collected_items,
            selected_items=self._selected_items,
            assertions=self._assertions,
            options=self.pytest_session.config.option,
        )
        if self.report.num_unused:
            if self.update_snapshots:
                self.remove_unused_snapshots(
                    unused_snapshot_collections=self.report.unused,
                    used_snapshot_collections=self.report.used,
                )
            elif not self.warn_unused_snapshots:
                exitstatus |= EXIT_STATUS_FAIL_UNUSED
        return exitstatus

    def register_request(self, assertion: "SnapshotAssertion") -> None:
        self._assertions.append(assertion)

        test_location = assertion.extension.test_location.filepath
        extension_class = assertion.extension.__class__
        if extension_class not in self._locations_discovered[test_location]:
            self._locations_discovered[test_location].add(extension_class)
            discovered_extensions = {
                discovered.location: assertion.extension
                for discovered in assertion.extension.discover_snapshots()
                if discovered.has_snapshots
            }
            self._extensions.update(discovered_extensions)

    def remove_unused_snapshots(
        self,
        unused_snapshot_collections: "SnapshotCollections",
        used_snapshot_collections: "SnapshotCollections",
    ) -> None:
        """
        Remove all unused snapshots using the registed extension for the collection file
        If there is not registered extension and the location is unused delete the file
        """
        for unused_snapshot_collection in unused_snapshot_collections:
            snapshot_location = unused_snapshot_collection.location

            extension = self._extensions.get(snapshot_location)
            if extension:
                extension.delete_snapshots(
                    snapshot_location=snapshot_location,
                    snapshot_names={
                        snapshot.name for snapshot in unused_snapshot_collection
                    },
                )
            elif snapshot_location not in used_snapshot_collections:
                Path(snapshot_location).unlink()

    @staticmethod
    def filter_valid_items(items: List["pytest.Item"]) -> Iterable["pytest.Item"]:
        return (item for item in items if isinstance(item, pytest.Function))
