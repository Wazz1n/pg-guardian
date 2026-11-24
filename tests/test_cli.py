from typer.testing import CliRunner

from pg_guardian.cli import app

runner = CliRunner()


def test_backup_prints_digest_on_a_single_line(monkeypatch, tmp_path):
    digest = "0123456789abcdef" * 4
    monkeypatch.setattr(
        "pg_guardian.cli.create_verified_backup",
        lambda dsn, out: (tmp_path / "backup.sql.gz", digest),
    )

    result = runner.invoke(
        app,
        ["backup", "--dsn", "postgresql://u:p@localhost/db", "--out", str(tmp_path)],
        env={"COLUMNS": "40"},
    )

    assert result.exit_code == 0
    assert digest in result.output
