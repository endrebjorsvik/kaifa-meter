
import click
from kaifa_meter.reader import read_serial


@click.group()
def cli():
    pass


@cli.command()
@click.argument('device')
def serial(device):
    read_serial(device)


@cli.command()
def initdb():
    print('InitDb')


if __name__ == '__main__':
    cli()
