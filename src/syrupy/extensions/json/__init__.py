import datetime
import inspect
import json
from collections import OrderedDict
from types import (
    FunctionType,
    GeneratorType,
)
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
)

from syrupy.constants import SYMBOL_ELLIPSIS
from syrupy.extensions.amber.serializer import Repr
from syrupy.extensions.single_file import (
    SingleFileSnapshotExtension,
    WriteMode,
)

if TYPE_CHECKING:
    from syrupy.types import (
        PropertyFilter,
        PropertyMatcher,
        PropertyPath,
        SerializableData,
        SerializedData,
    )


class JSONSnapshotExtension(SingleFileSnapshotExtension):
    _max_depth: int = 99
    _write_mode = WriteMode.TEXT
    _file_extension = "json"

    @classmethod
    def sort(cls, iterable: Iterable[Any]) -> Iterable[Any]:
        try:
            return sorted(iterable)
        except TypeError:
            return sorted(iterable, key=str)

    @classmethod
    def __is_namedtuple(cls, obj: Any) -> bool:
        return isinstance(obj, tuple) and all(
            isinstance(n, (str,)) for n in getattr(obj, "_fields", [None])
        )

    @classmethod
    def _filter(
        cls,
        data: "SerializableData",
        *,
        depth: int = 0,
        path: "PropertyPath",
        exclude: Optional["PropertyFilter"] = None,
        include: Optional["PropertyFilter"] = None,
        matcher: Optional["PropertyMatcher"] = None,
        visited: Optional[Set[Any]] = None,
    ) -> "SerializableData":
        data_id = id(data)
        visited = set() if visited is None else visited
        if depth > cls._max_depth or data_id in visited:
            data = Repr(SYMBOL_ELLIPSIS)
        elif matcher:
            data = matcher(data=data, path=path)

        if isinstance(data, (int, float, str)) or data is None:
            return data

        filtered_dct: Dict[Any, Any]
        if isinstance(data, (dict,)):
            filtered_dct = OrderedDict()
            keys = (
                cls.sort(data.keys())
                if not isinstance(data, (OrderedDict,))
                else data.keys()
            )
            for key in keys:
                value = data[key]
                if exclude and exclude(prop=key, path=path):
                    continue
                if include and not include(prop=key, path=path):
                    continue
                if not isinstance(key, (str,)):
                    continue
                filtered_dct[key] = cls._filter(
                    data=value,
                    depth=depth + 1,
                    path=(*path, (key, type(value))),
                    exclude=exclude,
                    include=include,
                    matcher=matcher,
                    visited={*visited, data_id},
                )
            return filtered_dct

        if cls.__is_namedtuple(data):
            filtered_dct = OrderedDict()
            for key in cls.sort(data._fields):
                value = getattr(data, key)
                filtered_dct[key] = cls._filter(
                    data=value,
                    depth=depth + 1,
                    path=(*path, (key, type(value))),
                    exclude=exclude,
                    include=include,
                    matcher=matcher,
                    visited={*visited, data_id},
                )
            return filtered_dct

        if isinstance(data, (set, frozenset, list, tuple, GeneratorType)):
            filtered_lst: List[Any] = []
            iterable = (
                cls.sort(data) if isinstance(data, (set, frozenset)) else list(data)
            )
            for key, value in enumerate(iterable):
                filtered_lst.append(
                    cls._filter(
                        data=value,
                        depth=depth + 1,
                        path=(*path, (key, type(value))),
                        exclude=exclude,
                        include=include,
                        matcher=matcher,
                        visited={*visited, data_id},
                    )
                )
            return filtered_lst

        if isinstance(data, (datetime.datetime,)):
            return data.strftime("%Y-%m-%dT%H:%M:%S.%f%z")

        if isinstance(data, FunctionType):
            return (
                f"<{FunctionType.__name__} "
                f"{data.__qualname__}{str(inspect.signature(data))}>"
            )

        if data.__class__.__repr__ != object.__repr__:
            return repr(data)

        return f"<class '{data.__class__.__name__}'>"

    def serialize(
        self,
        data: "SerializableData",
        *,
        exclude: Optional["PropertyFilter"] = None,
        include: Optional["PropertyFilter"] = None,
        matcher: Optional["PropertyMatcher"] = None,
        **kwargs: Any,
    ) -> "SerializedData":
        data = self._filter(
            data=data,
            depth=0,
            path=(),
            exclude=exclude,
            include=include,
            matcher=matcher,
        )
        return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
