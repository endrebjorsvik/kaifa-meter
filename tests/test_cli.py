import pathlib

from click.testing import CliRunner

from kaifa_meter import cli

DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
SAMPLE_FILE = DATA_DIR / "dump-2018-11-18T20:27:54.823083.dat"


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["--help"])
    assert result.exit_code == 0
    assert "Command line tool that reads, parses and stores" in result.output
    assert "parse-file" in result.output
    assert "serial" in result.output
    assert "initdb" in result.output


def test_file_writer(tmp_path: pathlib.Path):
    out_file = tmp_path / "out.txt"
    _ = cli.FileWriter(out_file)
    assert out_file.exists()
    assert out_file.read_text(encoding="utf-8") == ""


def test_get_output_handler(tmp_path: pathlib.Path):
    out_file = tmp_path / "out.txt"
    handler_file = cli.get_output_handler(out_file, None, "", "")
    assert handler_file is not None

    handler_none = cli.get_output_handler(None, None, "", "")
    assert handler_none is None


def test_parse_file_stdout():
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["parse-file", str(SAMPLE_FILE)])
    assert result.exit_code == 0
    assert "items_count = 1" in result.output
    assert "pwr_act_pos = 601" in result.output


def test_parse_file_to_outfile(tmp_path: pathlib.Path):
    runner = CliRunner()
    out_file = tmp_path / "parsed.txt"
    result = runner.invoke(
        cli.cli, ["parse-file", str(SAMPLE_FILE), "-o", str(out_file)]
    )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "items_count = 1" in content
    assert "pwr_act_pos = 601" in content
