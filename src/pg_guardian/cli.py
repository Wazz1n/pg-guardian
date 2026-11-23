import subprocess
from pathlib import Path
from typing import Annotated, NoReturn

import psycopg
import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from pg_guardian.backup import create_verified_backup
from pg_guardian.db import get_schema_summary

app = typer.Typer(
    help="pg-guardian: PostgreSQL audit and backup CLI.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)

DsnOption = Annotated[
    str,
    typer.Option(envvar="DATABASE_URL", help="PostgreSQL connection URI."),
]
SchemaOption = Annotated[str, typer.Option(help="Schema to audit.")]
OutOption = Annotated[Path, typer.Option(help="Destination folder.")]


def _fail(message: str) -> NoReturn:
    err_console.print(f"[bold red]Error:[/bold red] {escape(message)}")
    raise typer.Exit(code=1)


@app.command("inspect")
def inspect_schema(dsn: DsnOption, schema: SchemaOption = "public") -> None:
    """Audit tables, sizes and index counts of a schema."""
    try:
        rows = get_schema_summary(dsn, schema)
    except psycopg.Error as exc:
        _fail(f"Could not query the database: {exc}")

    if not rows:
        console.print(f"No tables found in schema '{escape(schema)}'.")
        return

    table = Table(title=f"PostgreSQL Schema Audit ({escape(schema)})")
    table.add_column("Table", style="cyan")
    table.add_column("Size", justify="right")
    table.add_column("Est. Rows", justify="right")
    table.add_column("Indexes", justify="right")

    for row in rows:
        count = row["index_count"]
        style = "bold red" if count == 0 else "green"
        table.add_row(
            escape(row["table_name"]),
            row["total_size"],
            str(row["estimated_rows"]),
            f"[{style}]{count}[/{style}]",
        )

    console.print(table)

    unindexed = sum(1 for row in rows if row["index_count"] == 0)
    if unindexed:
        console.print(f"[bold red]{unindexed}[/bold red] table(s) have no index at all.")


@app.command()
def backup(dsn: DsnOption, out: OutOption = Path("./backups")) -> None:
    """Create a gzip-compressed backup with SHA-256 verification."""
    try:
        archive, digest = create_verified_backup(dsn, out)
    except FileNotFoundError:
        _fail("pg_dump was not found. Install the PostgreSQL client tools.")
    except subprocess.CalledProcessError:
        _fail("pg_dump failed. Check the connection details and your permissions.")
    except psycopg.Error:
        _fail("The connection string is not valid.")
    except OSError as exc:
        _fail(f"Could not write the backup: {exc}")

    console.print(f"[bold green]Backup created:[/bold green] {escape(str(archive))}")
    console.print(f"[bold]SHA-256:[/bold] {digest}")
