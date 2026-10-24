from pathlib import Path
import subprocess

from cme_weather.version import software_version


def test_build_metadata_without_git(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "2.3.4-rc.1+build.7")
    monkeypatch.setenv("PATH", "/nonexistent")
    assert software_version() == "2.3.4-rc.1+build.7"


def test_native_git_checkout(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    root = Path(__file__).resolve().parents[1]
    expected = subprocess.check_output(["sh", str(root / "tools/version.sh")], text=True).strip()
    assert software_version() == expected


def test_unknown_without_metadata_or_git(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.setenv("PATH", "/nonexistent")
    assert software_version() == "0.0.0+unknown"
