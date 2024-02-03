import warnings
from abc import (
    ABC,
    abstractmethod,
)
from gettext import gettext
from itertools import zip_longest
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
)

from syrupy.constants import (
    DISABLE_COLOR_ENV_VAR,
    SNAPSHOT_DIRNAME,
    SYMBOL_CARRIAGE,
    SYMBOL_ELLIPSIS,
    SYMBOL_NEW_LINE,
)
from syrupy.data import (
    DiffedLine,
    Snapshot,
    SnapshotCollection,
    SnapshotCollections,
    SnapshotEmptyCollection,
)
from syrupy.exceptions import SnapshotDoesNotExist
from syrupy.terminal import (
    context_style,
    received_diff_style,
    received_style,
    reset,
    snapshot_diff_style,
    snapshot_style,
)
from syrupy.utils import (
    env_context,
    obj_attrs,
    qdiff,
    walk_snapshot_dir,
)

if TYPE_CHECKING:
    from syrupy.location import PyTestLocation
    from syrupy.types import (
        PropertyFilter,
        PropertyMatcher,
        SerializableData,
        SerializedData,
        SnapshotIndex,
    )


class SnapshotSerializer(ABC):
    @abstractmethod
    def serialize(
        self,
        data: "SerializableData",
        *,
        exclude: Optional["PropertyFilter"] = None,
        include: Optional["PropertyFilter"] = None,
        matcher: Optional["PropertyMatcher"] = None,
    ) -> "SerializedData":
        """
        Serializes a python object / data structure into a string
        to be used for comparison with snapshot data from disk.
        """
        raise NotImplementedError


class SnapshotCollectionStorage(ABC):
    _file_extension = ""

    @classmethod
    def get_snapshot_name(
        cls,
        *,
        test_location: "PyTestLocation",
        index: "SnapshotIndex" = 0,
    ) -> str:
        """Get the snapshot name for the assertion index in a test location"""
        index_suffix = ""
        if isinstance(index, (str,)):
            index_suffix = f"[{index}]"
        elif index:
            index_suffix = f".{index}"
        return f"{test_location.snapshot_name}{index_suffix}"

    @classmethod
    def get_location(
        cls, *, test_location: "PyTestLocation", index: "SnapshotIndex"
    ) -> str:
        """Returns full filepath where snapshot data is stored."""
        basename = cls._get_file_basename(test_location=test_location, index=index)
        fileext = f".{cls._file_extension}" if cls._file_extension else ""
        return str(
            Path(cls.dirname(test_location=test_location)).joinpath(
                f"{basename}{fileext}"
            )
        )

    def is_snapshot_location(self, *, location: str) -> bool:
        """Checks if supplied location is valid for this snapshot extension"""
        return location.endswith(self._file_extension)

    def discover_snapshots(
        self, *, test_location: "PyTestLocation"
    ) -> "SnapshotCollections":
        """
        Returns all snapshot collections in test site
        """
        discovered: "SnapshotCollections" = SnapshotCollections()
        for filepath in walk_snapshot_dir(self.dirname(test_location=test_location)):
            if self.is_snapshot_location(location=filepath):
                snapshot_collection = self._read_snapshot_collection(
                    snapshot_location=filepath
                )
                if not snapshot_collection.has_snapshots:
                    snapshot_collection = SnapshotEmptyCollection(location=filepath)
            else:
                snapshot_collection = SnapshotCollection(location=filepath)

            discovered.add(snapshot_collection)

        return discovered

    def read_snapshot(
        self,
        *,
        test_location: "PyTestLocation",
        index: "SnapshotIndex",
        session_id: str,
    ) -> "SerializedData":
        """
        This method is _final_, do not override. You can override
        `_read_snapshot_data_from_location` in a subclass to change behaviour.
        """
        snapshot_location = self.get_location(test_location=test_location, index=index)
        snapshot_name = self.get_snapshot_name(test_location=test_location, index=index)
        snapshot_data = self._read_snapshot_data_from_location(
            snapshot_location=snapshot_location,
            snapshot_name=snapshot_name,
            session_id=session_id,
        )
        if snapshot_data is None:
            raise SnapshotDoesNotExist()
        return snapshot_data

    @classmethod
    def write_snapshot(
        cls,
        *,
        snapshot_location: str,
        snapshots: List[Tuple["SerializedData", "PyTestLocation", "SnapshotIndex"]],
    ) -> None:
        """
        This method is _final_, do not override. You can override
        `_write_snapshot_collection` in a subclass to change behaviour.
        """
        if not snapshots:
            return

        # First we group by location since it'll let us batch by file on disk.
        # Not as useful for single file snapshots, but useful for the standard
        # Amber extension.
        snapshot_collection = SnapshotCollection(location=snapshot_location)
        for data, test_location, index in snapshots:
            snapshot_name = cls.get_snapshot_name(
                test_location=test_location, index=index
            )
            snapshot = Snapshot(name=snapshot_name, data=data)
            snapshot_collection.add(snapshot)

            if not test_location.matches_snapshot_location(snapshot_location):
                warning_msg = gettext(
                    "{line_end}Can not relate snapshot location '{}' "
                    "to the test location.{line_end}"
                    "Consider adding '{}' to the generated location."
                ).format(
                    snapshot_location,
                    test_location.basename,
                    line_end="\n",
                )
                warnings.warn(warning_msg, stacklevel=1)

            if not test_location.matches_snapshot_name(snapshot.name):
                warning_msg = gettext(
                    "{line_end}Can not relate snapshot name '{}' "
                    "to the test location.{line_end}"
                    "Consider adding '{}' to the generated name."
                ).format(
                    snapshot.name,
                    test_location.testname,
                    line_end="\n",
                )
                warnings.warn(warning_msg, stacklevel=1)

        # Ensures the folder path for the snapshot file exists.
        Path(snapshot_location).parent.mkdir(parents=True, exist_ok=True)

        cls._write_snapshot_collection(snapshot_collection=snapshot_collection)

    @abstractmethod
    def delete_snapshots(
        self, *, snapshot_location: str, snapshot_names: Set[str]
    ) -> None:
        """
        Remove snapshots from a snapshot file.
        If the snapshot file will be empty remove the entire file.
        """
        raise NotImplementedError

    @abstractmethod
    def _read_snapshot_collection(
        self, *, snapshot_location: str
    ) -> "SnapshotCollection":
        """
        Read the snapshot location and construct a snapshot collection object
        """
        raise NotImplementedError

    @abstractmethod
    def _read_snapshot_data_from_location(
        self,
        *,
        snapshot_location: str,
        snapshot_name: str,
        session_id: str,
    ) -> Optional["SerializedData"]:
        """
        Get only the snapshot data from location for assertion
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def _write_snapshot_collection(
        cls, *, snapshot_collection: "SnapshotCollection"
    ) -> None:
        """
        Adds the snapshot data to the snapshots in collection location
        """
        raise NotImplementedError

    @classmethod
    def dirname(cls, *, test_location: "PyTestLocation") -> str:
        test_dir = Path(test_location.filepath).parent
        return str(test_dir.joinpath(SNAPSHOT_DIRNAME))

    @classmethod
    def _get_file_basename(
        cls, *, test_location: "PyTestLocation", index: "SnapshotIndex"
    ) -> str:
        """Returns file basename without extension. Used to create full filepath."""
        return test_location.basename


class SnapshotReporter(ABC):
    _context_line_count = 1

    def diff_snapshots(
        self,
        serialized_data: "SerializedData",
        snapshot_data: "SerializedData",
    ) -> "SerializedData":
        env = {DISABLE_COLOR_ENV_VAR: "true"}
        attrs = {"_context_line_count": 0}
        with env_context(**env), obj_attrs(self, attrs):
            return "\n".join(self.diff_lines(serialized_data, snapshot_data))

    def diff_lines(
        self,
        serialized_data: "SerializedData",
        snapshot_data: "SerializedData",
    ) -> Iterator[str]:
        for line in self.__diff_lines(str(snapshot_data), str(serialized_data)):
            yield reset(line)

    @property
    def _ends(self) -> Dict[str, str]:
        return {"\n": self._marker_new_line, "\r": self._marker_carriage}

    @property
    def _context_line_max(self) -> int:
        return self._context_line_count * 2

    @property
    def _marker_context_max(self) -> str:
        return SYMBOL_ELLIPSIS

    @property
    def _marker_new_line(self) -> str:
        return SYMBOL_NEW_LINE

    @property
    def _marker_carriage(self) -> str:
        return SYMBOL_CARRIAGE

    def __diff_lines(self, a: str, b: str) -> Iterator[str]:
        for line in self.__diffed_lines(a, b):
            show_ends = (
                self.__strip_ends(line.a[1:] if line.a is not None else "")
                == self.__strip_ends(line.b[1:] if line.b is not None else "")
                if line.is_complete
                else False
            )
            if line.has_snapshot and line.a is not None:
                yield self.__format_line(
                    line.a, line.diff_a, snapshot_style, snapshot_diff_style, show_ends
                )
            if line.has_received and line.b is not None:
                yield self.__format_line(
                    line.b, line.diff_b, received_style, received_diff_style, show_ends
                )
            yield from map(context_style, self.__limit_context(line.c))

    def __diffed_lines(self, a: str, b: str) -> Iterator["DiffedLine"]:
        staged_diffed_line: Optional["DiffedLine"] = None
        for line in qdiff(a.splitlines(keepends=True), b.splitlines(keepends=True)):
            is_context_line = line[0] == " "
            is_snapshot_line = line[0] == "-"
            is_received_line = line[0] == "+"
            is_diff_line = line[0] == "?"

            if is_context_line or is_diff_line:
                line = self.__strip_ends(line)

            if staged_diffed_line:
                if is_diff_line:
                    if staged_diffed_line.has_received:
                        staged_diffed_line.diff_b = line
                    elif staged_diffed_line.has_snapshot:
                        staged_diffed_line.diff_a = line
                    # else: should never happen because then it would have
                    # encounted a diff line without any previously staged line
                else:
                    should_unstage = (
                        staged_diffed_line.is_complete
                        or (staged_diffed_line.has_snapshot and is_snapshot_line)
                        or (staged_diffed_line.has_received and is_received_line)
                        or (staged_diffed_line.is_context and not is_context_line)
                    )
                    if should_unstage:
                        yield staged_diffed_line
                        staged_diffed_line = None
                    elif is_snapshot_line:
                        staged_diffed_line.a = line
                    elif is_received_line:
                        staged_diffed_line.b = line
                    elif is_context_line:
                        staged_diffed_line.c.append(line)

            if not staged_diffed_line:
                if is_snapshot_line:
                    staged_diffed_line = DiffedLine(a=line)
                elif is_received_line:
                    staged_diffed_line = DiffedLine(b=line)
                elif is_context_line:
                    staged_diffed_line = DiffedLine(c=[line])
                # else: should never happen because then it would have
                # encounted a diff line without any previously staged line

        if staged_diffed_line:
            yield staged_diffed_line

    def __format_line(
        self,
        line: str,
        diff_markers: str,
        line_style: Callable[[str], str],
        diff_style: Callable[[str], str],
        show_ends: bool,
    ) -> str:
        if show_ends:
            for old, new in self._ends.items():
                line = line.replace(old, new)
        else:
            line = self.__strip_ends(line)
        return "".join(
            diff_style(char) if str(marker) in "-+^" else line_style(char)
            for marker, char in zip_longest(diff_markers.rstrip(), line)
            if char is not None
        )

    def __limit_context(self, lines: List[str]) -> Iterator[str]:
        yield from lines[: self._context_line_count]
        num_lines = len(lines)
        if num_lines:
            if num_lines > self._context_line_max:
                count_leading_whitespace: Callable[[str], int] = lambda s: len(s) - len(
                    s.lstrip()
                )
                if self._context_line_count:
                    num_space = (
                        count_leading_whitespace(lines[self._context_line_count - 1])
                        + count_leading_whitespace(lines[-self._context_line_count])
                    ) // 2
                else:
                    num_space = count_leading_whitespace(lines[num_lines // 2])
                yield " " * num_space + self._marker_context_max
            if self._context_line_count and num_lines > 1:
                yield from lines[-self._context_line_count :]  # noqa: E203

    def __strip_ends(self, line: str) -> str:
        return line.rstrip("".join(self._ends.keys()))


class SnapshotComparator:
    def matches(
        self,
        *,
        serialized_data: "SerializableData",
        snapshot_data: "SerializableData",
    ) -> bool:
        """
        Compares serialized data and snapshot data and returns
        whether they match.
        """
        return bool(serialized_data == snapshot_data)


class AbstractSyrupyExtension(
    SnapshotSerializer, SnapshotCollectionStorage, SnapshotReporter, SnapshotComparator
):
    pass
