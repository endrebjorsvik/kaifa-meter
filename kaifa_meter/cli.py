import dataclasses
import pathlib
from collections.abc import Callable

import click

from kaifa_meter import db_writer, decoder, reader

type FrameCallback = Callable[[decoder.DecodedFrame], None]


@dataclasses.dataclass(slots=True)
class FileWriter:
    filename: pathlib.Path

    def __post_init__(self) -> None:
        self.filename.write_text("", encoding="utf-8")

    def write(self, msg: decoder.DecodedFrame) -> None:
        with self.filename.open("a", encoding="utf-8") as fp:
            fp.write(str(msg))


def get_output_handler(
    outfile: pathlib.Path | None,
    dbname: str | None,
    dbuser: str,
    dbtable: str,
) -> FrameCallback | None:
    """Resolve destination callback based on CLI options."""
    match (outfile, dbname):
        case (pathlib.Path() as path, _):
            writer = FileWriter(path)
            return writer.write
        case (_, str()):
            db = db_writer.DbWriter(dbname, dbuser, dbtable)
            return db.write
        case _:
            return None


@click.group()
def cli() -> None:
    """Command line tool that reads, parses and stores
    measurement data from Kaifa electricity meters."""


@cli.command()
@click.argument("device")
@click.option(
    "-o",
    "--outfile",
    type=click.Path(dir_okay=False, path_type=pathlib.Path),
    help="File to write parsed data. Default stdout.",
)
@click.option("--dbname", help="Database to write parsed data.")
@click.option("--dbuser", help="Username for database.", default="")
@click.option("--dbtable", help="Table to use in database.", default="")
def serial(
    device: str,
    outfile: pathlib.Path | None,
    dbname: str | None,
    dbuser: str,
    dbtable: str,
) -> None:
    """Read data from serial device (TTY, UART, etc.).

    Write processed data to file if outfile is specified.
    Write to database if database is specified. Defaults to
    terminal output.
    """
    callback = get_output_handler(outfile, dbname, dbuser, dbtable)
    reader.read_serial(device, callback)


@cli.command()
@click.argument(
    "file",
    type=click.Path(exists=True, dir_okay=False, path_type=pathlib.Path),
)
@click.option(
    "-o",
    "--outfile",
    type=click.Path(dir_okay=False, path_type=pathlib.Path),
    help="File to write parsed data. Default stdout.",
)
@click.option("--dbname", help="Database to write parsed data.")
@click.option("--dbuser", help="Username for database.", default="")
@click.option("--dbtable", help="Table to use in database.", default="")
def parse_file(
    file: pathlib.Path,
    outfile: pathlib.Path | None,
    dbname: str | None,
    dbuser: str,
    dbtable: str,
) -> None:
    """Read data from an already captured file.

    Write processed data to file if outfile is specified.
    Write to database if database is specified. Defaults to
    terminal output.
    """
    msg = reader.read_file(file)
    handler = get_output_handler(outfile, dbname, dbuser, dbtable)
    if handler is not None:
        handler(msg)
    else:
        print(msg)


@cli.command()
@click.option("--dbname", required=True, help="Database name.")
@click.option("--dbuser", required=True, help="Username for database.")
@click.option("--dbtable", required=True, help="Table to use in database.")
def initdb(
    dbname: str,
    dbuser: str,
    dbtable: str,
) -> None:
    """Initialise database that will store measurement data."""
    db_writer.init_db(dbname, dbuser, dbtable)


if __name__ == "__main__":
    cli()
