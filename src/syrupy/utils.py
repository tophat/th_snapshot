import os
from typing import (
    Any,
    Generator,
    List,
    Optional,
    Set,
)

from .constants import SNAPSHOT_DIRNAME


def get_targeted_snapshots_from_targeted_files(
    targeted_files: Optional[Set[Any]],
) -> List[str]:
    if not targeted_files:
        return []

    split_paths = [file_path.split("/") for file_path in targeted_files]

    return [
        os.path.abspath(
            os.path.join(
                *[
                    *split_path[:-1],
                    SNAPSHOT_DIRNAME,
                    ".".join([os.path.splitext(split_path[-1])[0], "ambr"]),
                ]
            )
        )
        for split_path in split_paths
    ]


def in_snapshot_dir(path: str) -> bool:
    parts = path.split(os.path.sep)
    return SNAPSHOT_DIRNAME in parts


def walk_snapshot_dir(root: str) -> Generator[str, None, None]:
    for (dirpath, _, filenames) in os.walk(root):
        if not in_snapshot_dir(dirpath):
            continue
        for filename in filenames:
            if not filename.startswith("."):
                yield os.path.join(dirpath, filename)
