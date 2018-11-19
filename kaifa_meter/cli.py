import click
from kaifa_meter.reader import read_serial, read_file


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
    pass


@cli.command()
@click.argument('device')
@click.option('-o', '--outfile', help="File to write parsed data. Default stdout.")
def serial(device, outfile):
    callback = None
    if outfile is not None:
        w = FileWriter(outfile)
        callback = w.write

    read_serial(device, callback)


@cli.command()
@click.argument('file')
@click.option('-o', '--outfile', help="File to write parsed data. Default stdout.")
def parse(file, outfile):
    msg = read_file(file)
    if outfile is not None:
        w = FileWriter(outfile)
        w.write(msg)
    else:
        print(msg)
