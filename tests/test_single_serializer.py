import pytest

from .utils import clean_output


@pytest.fixture
def testcases(testdir):
    testdir.makeconftest(
        """
        import pytest

        from syrupy.extensions.raw_single import RawSingleSnapshotExtension
        from syrupy.extensions.image import (
            PNGImageSnapshotExtension,
            SVGImageSnapshotExtension,
        )


        @pytest.fixture
        def snapshot_raw(snapshot):
            return snapshot.use_extension(RawSingleSnapshotExtension)


        @pytest.fixture
        def snapshot_png(snapshot):
            return snapshot.use_extension(PNGImageSnapshotExtension)


        @pytest.fixture
        def snapshot_svg(snapshot):
            return snapshot.use_extension(SVGImageSnapshotExtension)
        """
    )
    return {
        "passed": (
            """
            def test_passed_raw(snapshot_raw):
                assert snapshot_raw == b'passed1'
                assert snapshot_raw == b'passed2'
            """
        ),
        "failed": (
            """
            def test_failed_raw(snapshot_raw):
                assert snapshot_raw == 'failed'

            def test_failed_image(snapshot_png):
                assert "not a byte string" == snapshot_png
            """
        ),
    }


@pytest.fixture
def testcases_updated(testcases):
    updated_testcases = {
        "passed": (
            """
            def test_passed_raw(snapshot_raw):
                assert snapshot_raw == b'passed'
            """
        )
    }
    return {**testcases, **updated_testcases}


def test_unsaved_snapshots(testdir, testcases):
    testdir.makepyfile(test_file=testcases["passed"])
    result = testdir.runpytest("-v")
    assert "Snapshot does not exist" in clean_output(result.stdout.str())
    assert result.ret == 1


def test_failed_snapshots(testdir, testcases):
    testdir.makepyfile(test_file=testcases["failed"])
    result = testdir.runpytest("-v", "--snapshot-update")
    assert "2 snapshots failed" in clean_output(result.stdout.str())
    assert result.ret == 1


@pytest.fixture
def stubs(testdir, testcases):
    testdir.makepyfile(test_file=testcases["passed"])
    return testdir.runpytest("-v", "--snapshot-update"), testdir, testcases


def test_generated_snapshots(stubs):
    result = stubs[0]
    result_stdout = clean_output(result.stdout.str())
    assert "2 snapshots generated" in result_stdout
    assert "snapshots unused" not in result_stdout
    assert result.ret == 0


def test_unmatched_snapshots(stubs, testcases_updated):
    testdir = stubs[1]
    testdir.makepyfile(test_file=testcases_updated["passed"])
    result = testdir.runpytest("-v")
    result_stdout = clean_output(result.stdout.str())
    assert "1 snapshot failed" in result_stdout
    assert "1 snapshot unused" in result_stdout
    assert result.ret == 1


def test_updated_snapshots(stubs, testcases_updated):
    testdir = stubs[1]
    testdir.makepyfile(test_file=testcases_updated["passed"])
    result = testdir.runpytest("-v", "--snapshot-update")
    result_stdout = clean_output(result.stdout.str())
    assert "1 snapshot updated" in result_stdout
    assert "1 unused snapshot deleted" in result_stdout
    assert result.ret == 0
