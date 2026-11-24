import gzip
import hashlib
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from psycopg.conninfo import conninfo_to_dict

CHUNK_SIZE = 1024 * 1024  # 1 MB


def _pg_env(dsn: str) -> dict[str, str]:
    params = conninfo_to_dict(dsn)
    mapping = {
        "host": "PGHOST",
        "port": "PGPORT",
        "user": "PGUSER",
        "password": "PGPASSWORD",
        "dbname": "PGDATABASE",
        "sslmode": "PGSSLMODE",
    }
    env = os.environ.copy()
    for key, var in mapping.items():
        if key in params:
            env[var] = str(params[key])
    return env


def _sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_verified_backup(dsn: str, output_dir: Path) -> tuple[Path, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    gz_path = output_dir / f"backup_{timestamp}.sql.gz"

    process = subprocess.Popen(["pg_dump"], env=_pg_env(dsn), stdout=subprocess.PIPE)
    with gzip.open(gz_path, "wb") as f_out:
        for chunk in iter(lambda: process.stdout.read(CHUNK_SIZE), b""):
            f_out.write(chunk)
    return_code = process.wait()
    if return_code != 0:
        gz_path.unlink(missing_ok=True)
        raise subprocess.CalledProcessError(return_code, "pg_dump")

    sha256 = _sha256_of_file(gz_path)
    checksum_path = gz_path.parent / (gz_path.name + ".sha256")
    checksum_path.write_text(f"{sha256}  {gz_path.name}\n", encoding="utf-8")
    return gz_path, sha256
