import pathlib

import click
from kaifa_meter import decoder
from kaifa_meter import reader
from kaifa_meter import db_writer


class FileWriter:
    filename: pathlib.Path

    def __init__(self, filename: pathlib.Path):
        self.filename = filename
        with self.filename.open("w") as fp:
            fp.write("")

    def write(self, msg: decoder.DecodedFrame):
        with self.filename.open("a") as fp:
            fp.write(str(msg))


@click.group()
def cli():
    """Command line tool that reads, parses and stores
    measurement data from Kaifa electricity meters."""
    pass


@cli.command()
@click.argument("device")
@click.option("-o", "--outfile", help="File to write parsed data. Default stdout.")
@click.option("--dbname", help="Database to write parsed data.")
@click.option("--dbuser", help="Username for database.", default="")
@click.option("--dbtable", help="Table to use in database.", default="")
def serial(
    device: str,
    outfile: str | None,
    dbname: str | None,
    dbuser: str,
    dbtable: str,
):
    """Read data from serial device (TTY, UART, etc.).

    Write processed data to file if outfile is specified.
    Write to database if database is specified. Defaults to
    terminal output.
    """
    callback = None
    if outfile is not None:
        w = FileWriter(pathlib.Path(outfile))
        callback = w.write
    elif dbname is not None:
        db = db_writer.DbWriter(dbname, dbuser, dbtable)
        callback = db.write

    reader.read_serial(device, callback)


@cli.command()
@click.argument("file")
@click.option("-o", "--outfile", help="File to write parsed data. Default stdout.")
@click.option("--dbname", help="Database to write parsed data.")
@click.option("--dbuser", help="Username for database.", default="")
@click.option("--dbtable", help="Table to use in database.", default="")
@click.pass_context
def parse_file(
    ctx: click.Context,
    file: str,
    outfile: str | None,
    dbname: str | None,
    dbuser: str,
    dbtable: str,
):
    """Read data from an already captured file.

    Write processed data to file if outfile is specified.
    Write to database if database is specified. Defaults to
    terminal output.
    """
    msg = reader.read_file(file)
    if outfile is not None:
        w = FileWriter(pathlib.Path(outfile))
        w.write(msg)
    elif dbname is not None:
        db = db_writer.DbWriter(dbname, dbuser, dbtable)
        db.write(msg)
    else:
        print(msg)


@cli.command()
@click.option("--dbname", required=True)
@click.option("--dbuser", required=True)
@click.option("--dbtable", required=True)
def initdb(
    dbname: str,
    dbuser: str,
    dbtable: str,
):
    """Initialise database that will store measurement data."""
    db_writer.init_db(dbname, dbuser, dbtable)
