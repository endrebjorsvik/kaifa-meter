# kaifa-meter

## Introduction

This is a Python package that reads and decodes serial data from the HAN port of a few Kaifa electricity meters. It may be used as a Python library or as a standalone CLI.

Serial data frame decoding is fairly naive and based on inspiration from [roarfred](https://github.com/roarfred) and [Per Erik Nordbø](https://drive.google.com/drive/folders/0B3ZvFI0Dg1TDbDBzMU02cnU0Y28). It uses the [Construct](https://construct.readthedocs.io/en/latest/index.html) library to parse messages in a simple and straight-forward manner that is easily understood and maintainable.

The CLI writes decoded data to either:

- Terminal (pretty-printed)
- File (pretty-printed)
- PostgreSQL database

Feedback and improvement suggestions are welcome.

## Tested and supported meters

- MA105H2E

## Untested meters (but should work)

- MA304H3E
- MA304H4
- MA304T4
- MA304T4

## Installation

This package requires Python 3.6+. It depends on several third party packages, so I recommend installing it in a [virtualenv](https://virtualenv.pypa.io/en/latest/). It is packaged to be installed through [pip](https://pip.pypa.io/en/stable/) from GitHub.

    $ pip install git+https://github.com/endrebjorsvik/kaifa-meter.git

## Usage

Connect the electricity meter to a computer using a M-Bus-to-USB converter. It shall appear as a serial port (e.g. `/dev/ttyUSB0` or `COM3`). To print decoded data to your terminal, run

    $ kaifa_meter serial /dev/ttyUSB0

To save decoded data to file, run

    $ kaifa_meter serial /dev/ttyUSB0 -o /path/to/outfile.txt

It is also possible to dump all data to a PostgreSQL database. To test the database setup, run

    $ kaifa_meter initdb --dbname=<name of database> --dbuser=<name of database user> --dbtable=<table to create in database>

You can then dump data directly to the database by

    $ kaifa_meter serial /dev/ttyUSB0 --dbname=db --dbuser=user --dbtable=table

## Tested platforms

- Linux

## Hardware

The package is tested on a Kaifa MA105H2E meter that is connected to a computer through the following cabling:

- M-Bus-to-TTL/UART using [TI TSS721A](http://www.ti.com/product/TSS721A). Assembled PCBs are available from AliExpress.
- PL2303 TTL/UART-to-USB converter. Higher quality TTL converters from FTDI should also work.
