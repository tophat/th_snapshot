import re
from gettext import gettext
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Optional,
    Tuple,
)

from syrupy.extensions.amber.serializer import (
    AmberDataSerializer,
    Repr,
)

if TYPE_CHECKING:
    from syrupy.types import (
        PropertyMatcher,
        PropertyPath,
        PropertyValueType,
        SerializableData,
    )

    try:
        MatchResult = Optional[re.Match[str]]
    except TypeError:
        globals()["MatchResult"] = Optional[re.Match]
    Replacer = Callable[[SerializableData, MatchResult], SerializableData]


class PathTypeError(TypeError):
    pass


class StrictPathTypeError(PathTypeError):
    pass


def path_type(
    mapping: Optional[Dict[str, Tuple["PropertyValueType", ...]]] = None,
    *,
    types: Tuple["PropertyValueType", ...] = (),
    strict: bool = True,
    regex: bool = False,
    replacer: "Replacer" = lambda data, _: Repr(AmberDataSerializer.object_type(data)),
) -> "PropertyMatcher":
    """
    Factory to create a matcher using path and type mapping.
    Usecase:
    Replacing all values of certain types at specified paths.
    with their class name instead. Allows for deterministic
    snapshots on non-deterministic class e.g. datetime, random etc.
    """
    if not mapping and not types:
        raise PathTypeError(gettext("Both mapping and types argument cannot be empty"))

    def path_type_matcher(
        *, data: "SerializableData", path: "PropertyPath"
    ) -> Optional["SerializableData"]:
        path_str = ".".join(str(p) for p, _ in path)
        if mapping:
            for pattern in mapping:
                matches = _path_match(path_str, pattern, regex)
                if matches:
                    for type_to_match in mapping[pattern]:
                        if isinstance(data, type_to_match):
                            return replacer(data, matches)
                    if strict:
                        raise StrictPathTypeError(
                            gettext(
                                "{} at '{}' of type {} does not "
                                "match any of the expected types: {}"
                            ).format(data, path_str, data.__class__, mapping[pattern])
                        )
        for type_to_match in types:
            if isinstance(data, type_to_match):
                return replacer(data, None)
        return data

    return path_type_matcher


def path_value(
    mapping: Dict[str, str],
    *,
    types: Tuple["PropertyValueType", ...],
    replacer: "Replacer",
    **kwargs: Any,
) -> "PropertyMatcher":
    """
    Matches the path regex against the string repr of values for the types specified
    """

    kwargs["mapping"] = {path_pattern: types for path_pattern in mapping}
    kwargs["replacer"] = lambda data, path_matches: (
        replacer(
            data,
            _path_match(
                str(data), mapping[path_matches.re.pattern], kwargs.get("regex", False)
            ),
        )
        if path_matches.re.pattern in mapping
        else data
    )
    return path_type(**kwargs)


def _path_match(path: str, pattern: str, is_regex: bool) -> "MatchResult":
    """Match path against regular string or regex pattern"""
    if not is_regex:
        pattern = re.escape(pattern)
    return re.fullmatch(pattern, path)


def compose_matchers(*matchers: "PropertyMatcher") -> "PropertyMatcher":
    """
    Composes 1 or more matchers into a single matcher.
    """

    def _matcher(
        *, data: "SerializableData", path: "PropertyPath"
    ) -> Optional["SerializableData"]:
        for matcher in matchers:
            try:
                data = matcher(data=data, path=path)
            except StrictPathTypeError:
                # ignore strict mode when composing matchers
                pass

        return data

    return _matcher
