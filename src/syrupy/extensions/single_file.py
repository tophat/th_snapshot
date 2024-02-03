from enum import Enum
from gettext import gettext
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Optional,
    Set,
    Type,
    Union,
)
from unicodedata import category

from syrupy.constants import TEXT_ENCODING
from syrupy.data import (
    Snapshot,
    SnapshotCollection,
)
from syrupy.location import PyTestLocation

from .base import AbstractSyrupyExtension

if TYPE_CHECKING:
    from syrupy.types import (
        PropertyFilter,
        PropertyMatcher,
        SerializableData,
        SerializedData,
        SnapshotIndex,
    )


class WriteMode(Enum):
    BINARY = "b"
    TEXT = "t"

    def __str__(self) -> str:
        return self.value


class SingleFileSnapshotExtension(AbstractSyrupyExtension):
    _text_encoding = TEXT_ENCODING
    _write_mode = WriteMode.BINARY
    _file_extension = "raw"

    def serialize(
        self,
        data: "SerializableData",
        *,
        exclude: Optional["PropertyFilter"] = None,
        include: Optional["PropertyFilter"] = None,
        matcher: Optional["PropertyMatcher"] = None,
    ) -> "SerializedData":
        return self.get_supported_dataclass()(data)

    @classmethod
    def get_snapshot_name(
        cls,
        *,
        test_location: "PyTestLocation",
        index: "SnapshotIndex" = 0,
    ) -> str:
        return cls.__clean_filename(
            AbstractSyrupyExtension.get_snapshot_name(
                test_location=test_location, index=index
            )
        )

    def delete_snapshots(
        self, *, snapshot_location: str, snapshot_names: Set[str]
    ) -> None:
        Path(snapshot_location).unlink()

    @classmethod
    def _get_file_basename(
        cls, *, test_location: "PyTestLocation", index: "SnapshotIndex"
    ) -> str:
        return cls.get_snapshot_name(test_location=test_location, index=index)

    @classmethod
    def dirname(cls, *, test_location: "PyTestLocation") -> str:
        original_dirname = AbstractSyrupyExtension.dirname(test_location=test_location)
        return str(Path(original_dirname).joinpath(test_location.basename))

    def _read_snapshot_collection(
        self,
        *,
        snapshot_location: str,
    ) -> "SnapshotCollection":
        file_ext_len = len(self._file_extension) + 1 if self._file_extension else 0
        filename_wo_ext = snapshot_location[:-file_ext_len]
        basename = Path(filename_wo_ext).parts[-1]

        snapshot_collection = SnapshotCollection(location=snapshot_location)
        snapshot_collection.add(Snapshot(name=basename))
        return snapshot_collection

    def _read_snapshot_data_from_location(
        self,
        *,
        snapshot_location: str,
        snapshot_name: str,
        session_id: str,
    ) -> Optional["SerializableData"]:
        try:
            with open(
                snapshot_location,
                f"r{self._write_mode}",
                encoding=self.get_write_encoding(),
            ) as f:
                return f.read()
        except FileNotFoundError:
            return None

    @classmethod
    def get_supported_dataclass(cls) -> Union[Type[str], Type[bytes]]:
        if cls._write_mode == WriteMode.TEXT:
            return str
        return bytes

    @classmethod
    def get_write_encoding(cls) -> Optional[str]:
        if cls._write_mode == WriteMode.TEXT:
            return TEXT_ENCODING
        return None

    @classmethod
    def _write_snapshot_collection(
        cls,
        *,
        snapshot_collection: "SnapshotCollection",
    ) -> None:
        filepath, data = (
            snapshot_collection.location,
            next(iter(snapshot_collection)).data,
        )
        if not isinstance(data, cls.get_supported_dataclass()):
            error_text = gettext(
                "Can't write non supported data. Expected '{}', got '{}'"
            )
            raise TypeError(
                error_text.format(
                    cls.get_supported_dataclass().__name__, type(data).__name__
                )
            )
        with open(
            filepath, f"w{cls._write_mode}", encoding=cls.get_write_encoding()
        ) as f:
            f.write(data)

    @classmethod
    def __clean_filename(cls, filename: str) -> str:
        max_filename_length = 255 - len(cls._file_extension or "")
        exclude_chars = '\\/?*:|"<>'
        exclude_categ = ("C",)
        cleaned_filename = "".join(
            c
            for c in filename
            if c not in exclude_chars
            and not any(categ in category(c) for categ in exclude_categ)
        )
        return cleaned_filename[:max_filename_length]
