import gzip
import hashlib
import io
import subprocess

import pytest

from pg_guardian import backup
from pg_guardian.backup import create_verified_backup

DSN = "postgresql://alice:s3cret@localhost:5432/shop"


class FakeProcess:
    """Stand-in for the process returned by subprocess.Popen."""

    def __init__(self, data: bytes, returncode: int = 0):
        self.stdout = io.BytesIO(data)
        self._returncode = returncode

    def wait(self) -> int:
        return self._returncode


def test_backup_creates_gzip_and_checksum(tmp_path, monkeypatch):
    dump = b"-- fake dump\nCREATE TABLE demo (id int);\n"
    monkeypatch.setattr(backup.subprocess, "Popen", lambda *a, **k: FakeProcess(dump))

    gz_path, sha256 = create_verified_backup(DSN, tmp_path)

    assert gz_path.exists()
    assert gzip.decompress(gz_path.read_bytes()) == dump
    assert sha256 == hashlib.sha256(gz_path.read_bytes()).hexdigest()
    checksum_file = gz_path.parent / (gz_path.name + ".sha256")
    assert checksum_file.read_text() == f"{sha256}  {gz_path.name}\n"


def test_password_is_not_in_command_line(tmp_path, monkeypatch):
    captured = {}

    def fake_popen(args, **kwargs):
        captured["args"] = args
        captured["env"] = kwargs["env"]
        return FakeProcess(b"data")

    monkeypatch.setattr(backup.subprocess, "Popen", fake_popen)

    create_verified_backup(DSN, tmp_path)

    assert "s3cret" not in " ".join(captured["args"])
    assert captured["env"]["PGPASSWORD"] == "s3cret"
    assert captured["env"]["PGDATABASE"] == "shop"


def test_failed_dump_removes_partial_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        backup.subprocess, "Popen", lambda *a, **k: FakeProcess(b"partial", returncode=1)
    )

    with pytest.raises(subprocess.CalledProcessError):
        create_verified_backup(DSN, tmp_path)

    assert list(tmp_path.iterdir()) == []
