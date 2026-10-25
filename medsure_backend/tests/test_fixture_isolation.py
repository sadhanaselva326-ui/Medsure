"""test_fixture_isolation.py - Proves that CDSCOAlertAdapter and the ingestion CLI
refuse to load test/fixture files into production.

These tests do NOT touch the production database.  They exercise the path-guard
logic only, so they run quickly and require no async infrastructure.
"""

import os
import pytest

from scripts.data_ingestion.adapters.cdsco_adapter import _is_fixture_path, CDSCOAlertAdapter


# ---------------------------------------------------------------------------
# 1.  Unit tests for _is_fixture_path()
# ---------------------------------------------------------------------------

class TestIsFixturePath:
    """_is_fixture_path must identify forbidden paths without touching the filesystem."""

    def test_tests_dir_windows_style(self):
        """A path inside the tests\\ directory is always a fixture path."""
        p = r"C:\Users\Admin\project\medsure_backend\tests\fixtures\cdsco_nsq_alerts_fixture.json"
        assert _is_fixture_path(p) is True

    def test_tests_dir_posix_style(self):
        p = "/home/user/project/tests/fixtures/cdsco_nsq_alerts_fixture.json"
        assert _is_fixture_path(p) is True

    def test_fixture_in_filename(self):
        """A filename containing 'fixture' is rejected even outside tests/."""
        p = r"C:\data\cdsco_nsq_alerts_fixture.json"
        assert _is_fixture_path(p) is True

    def test_fixture_prefix_in_filename(self):
        p = "/downloads/cdsco/fixture_cdsco_alerts.json"
        assert _is_fixture_path(p) is True

    def test_real_download_path_accepted(self):
        """A path inside downloads/cdsco/ is NOT a fixture path."""
        p = r"C:\project\scripts\data_ingestion\downloads\cdsco\cdsco_nsq_alerts.json"
        assert _is_fixture_path(p) is False

    def test_data_dir_path_accepted(self):
        """The old data/ path is not inside tests/, so it passes the guard."""
        p = r"C:\project\scripts\data_ingestion\data\cdsco_nsq_alerts.json"
        assert _is_fixture_path(p) is False


# ---------------------------------------------------------------------------
# 2.  CDSCOAlertAdapter constructor guards
# ---------------------------------------------------------------------------

class TestCDSCOAdapterFixtureGuard:
    """CDSCOAlertAdapter.__init__ must raise ValueError for fixture paths."""

    def test_raises_for_tests_directory(self, tmp_path):
        """Adapter raises ValueError when given a path inside tests/."""
        fake_tests = tmp_path / "tests" / "fixtures"
        fake_tests.mkdir(parents=True)
        fixture_file = fake_tests / "cdsco_nsq_alerts_fixture.json"
        fixture_file.write_text("[]")

        with pytest.raises(ValueError, match="fixture"):
            CDSCOAlertAdapter(data_file_path=str(fixture_file))

    def test_raises_for_fixture_filename_outside_tests(self, tmp_path):
        """Adapter raises ValueError when filename contains 'fixture'."""
        fake_file = tmp_path / "fixture_cdsco.json"
        fake_file.write_text("[]")

        with pytest.raises(ValueError, match="fixture"):
            CDSCOAlertAdapter(data_file_path=str(fake_file))

    def test_accepts_real_download_path(self, tmp_path):
        """Adapter accepts a path in a downloads/ directory."""
        dl_dir = tmp_path / "downloads" / "cdsco"
        dl_dir.mkdir(parents=True)
        real_file = dl_dir / "cdsco_nsq_alerts.json"
        real_file.write_text("[]")

        adapter = CDSCOAlertAdapter(data_file_path=str(real_file))
        assert adapter.file_path == str(real_file)

    def test_raises_file_not_found_for_missing_non_fixture(self, tmp_path):
        """Adapter raises FileNotFoundError (not ValueError) for a missing non-fixture path."""
        missing = tmp_path / "downloads" / "cdsco_nsq_alerts.json"
        with pytest.raises(FileNotFoundError):
            CDSCOAlertAdapter(data_file_path=str(missing))

    def test_default_path_not_in_tests(self):
        """The default file_path must not contain 'tests' as a directory component."""
        import importlib
        mod = importlib.import_module("scripts.data_ingestion.adapters.cdsco_adapter")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(mod.__file__)))
        default_path = os.path.join(base_dir, "downloads", "cdsco", "cdsco_nsq_alerts.json")
        path_parts = [p.lower() for p in default_path.replace("\\", "/").split("/")]
        assert "tests" not in path_parts

    def test_default_path_is_downloads_not_data(self):
        """The default path must point to downloads/cdsco/, not data/."""
        import importlib
        mod = importlib.import_module("scripts.data_ingestion.adapters.cdsco_adapter")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(mod.__file__)))
        default_path = os.path.join(base_dir, "downloads", "cdsco", "cdsco_nsq_alerts.json")
        assert "downloads" in default_path
        # Ensure it does NOT point straight to the old data/ directory
        old_path = os.path.join(base_dir, "data", "cdsco_nsq_alerts.json")
        assert default_path != old_path


# ---------------------------------------------------------------------------
# 3.  Fixture file is ONLY in tests/fixtures/, not in the production data dir
# ---------------------------------------------------------------------------

class TestFixtureFileLocation:
    """The CDSCO fixture file must live only in tests/fixtures/."""

    BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_fixture_exists_in_tests_fixtures(self):
        fixture = os.path.join(self.BACKEND_ROOT, "tests", "fixtures", "cdsco_nsq_alerts_fixture.json")
        assert os.path.isfile(fixture), (
            f"Fixture file missing from tests/fixtures/: {fixture}"
        )

    def test_fixture_absent_from_production_data_dir(self):
        """The production data/ directory must NOT contain any cdsco alert file."""
        data_dir = os.path.join(
            self.BACKEND_ROOT, "scripts", "data_ingestion", "data"
        )
        if not os.path.isdir(data_dir):
            return
        for fname in os.listdir(data_dir):
            assert "cdsco" not in fname.lower(), (
                f"CDSCO file found in production data/ dir: {fname!r}. "
                "Move it to tests/fixtures/ and update CDSCOAlertAdapter."
            )

    def test_fixture_absent_from_downloads_dir(self):
        """The downloads/ directory must not contain any fixture-flagged cdsco file."""
        downloads = os.path.join(
            self.BACKEND_ROOT, "scripts", "data_ingestion", "downloads"
        )
        if not os.path.isdir(downloads):
            return
        for root, _dirs, files in os.walk(downloads):
            for fname in files:
                assert "fixture" not in fname.lower(), (
                    f"Fixture file found in downloads/: {os.path.join(root, fname)!r}. "
                    "Downloads must contain only real source data."
                )
