import click
from kaifa_meter.reader import read_serial, read_file
from kaifa_meter.db_writer import init_db, DbWriter


class FileWriter:
    def __init__(self, filename):
        self.filename = filename
        with open(self.filename, 'w') as fp:
            fp.write('')

    def write(self, msg):
        with open(self.filename, 'a') as fp:
            fp.write(str(msg))


@click.group()
def cli():
    """Command line tool that reads, parses and stores
       measurement data from Kaifa electricity meters."""
    pass


@cli.command()
@click.argument('device')
@click.option('-o', '--outfile', help="File to write parsed data. Default stdout.")
@click.option('--dbname', help="Database to write parsed data.")
@click.option('--dbuser', help="Username for database.", default='')
@click.option('--dbtable', help="Table to use in database.", default='')
def serial(device, outfile, dbname, dbuser, dbtable):
    """Read data from serial device (TTY, UART, etc.).

       Write processed data to file if outfile is specified.
       Write to database if database is specified. Defaults to
       terminal output.
    """
    callback = None
    if outfile is not None:
        w = FileWriter(outfile)
        callback = w.write
    elif dbname is not None:
        db = DbWriter(dbname, dbuser, dbtable)
        callback = db.write

    read_serial(device, callback)


@cli.command()
@click.argument('file')
@click.option('-o', '--outfile', help="File to write parsed data. Default stdout.")
@click.option('--dbname', help="Database to write parsed data.")
@click.option('--dbuser', help="Username for database.", default='')
@click.option('--dbtable', help="Table to use in database.", default='')
@click.pass_context
def parse_file(ctx, file, outfile, dbname, dbuser, dbtable):
    """Read data from an already captured file.

       Write processed data to file if outfile is specified.
       Write to database if database is specified. Defaults to
       terminal output.
    """
    msg = read_file(file)
    if outfile is not None:
        w = FileWriter(outfile)
        w.write(msg)
    elif dbname is not None:
        db = DbWriter(dbname, dbuser, dbtable)
        db.write(msg)
    else:
        print(msg)


@cli.command()
@click.option('--dbname', required=True)
@click.option('--dbuser', required=True)
@click.option('--dbtable', required=True)
def initdb(dbname, dbuser, dbtable):
    """Initialise database that will store measurement data."""
    init_db(dbname, dbuser, dbtable)
