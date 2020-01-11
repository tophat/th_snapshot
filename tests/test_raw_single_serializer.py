import os
from typing import TYPE_CHECKING

import pytest

from syrupy.data import (
    Snapshot,
    SnapshotCache,
)
from syrupy.extensions.raw_single import RawSingleSnapshotExtension


if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion


@pytest.fixture
def snapshot_raw(snapshot):
    return snapshot.use_extension(RawSingleSnapshotExtension)


def test_does_not_write_non_binary(testdir, snapshot_raw: "SnapshotAssertion"):
    snapshot_cache = SnapshotCache(
        location=os.path.join(testdir.tmpdir, "snapshot_cache.raw"),
    )
    snapshot_cache.add(Snapshot(name="snapshot_name", data="non binary data"))
    with pytest.raises(TypeError, match="Expected 'bytes', got 'str'"):
        snapshot_raw.extension._write_snapshot_cache(snapshot_cache=snapshot_cache)
    assert not os.path.exists(snapshot_cache.location)


class TestClass:
    def test_class_method_name(self, snapshot_raw):
        assert snapshot_raw == b"this is in a test class"

    @pytest.mark.parametrize("content", [b"x", b"y", b"z"])
    def test_class_method_parametrized(self, snapshot_raw, content):
        assert snapshot_raw == content
