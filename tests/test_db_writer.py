from unittest.mock import MagicMock, patch

from psycopg import sql

from kaifa_meter import db_writer, reader

DATA_DIR = __import__("pathlib").Path(__file__).parent.parent / "data"
SAMPLE_FILE = DATA_DIR / "dump-2018-11-18T20:27:43.126293.dat"


def test_init_table_creates_when_missing():
    cursor = MagicMock()
    cursor.fetchone.return_value = (False,)
    query = sql.SQL("CREATE TABLE test;").format()

    db_writer.init_table("test_table", cursor, query)

    cursor.execute.assert_any_call(
        "SELECT EXISTS(SELECT 1 FROM pg_tables WHERE tablename = %s);", ("test_table",)
    )
    cursor.execute.assert_called_with(query)


def test_init_table_skips_when_exists():
    cursor = MagicMock()
    cursor.fetchone.return_value = (True,)
    query = sql.SQL("CREATE TABLE test;").format()

    db_writer.init_table("test_table", cursor, query)

    assert cursor.execute.call_count == 1


def test_db_writer_lifecycle():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (True,)

    with patch("psycopg.connect") as mock_connect:
        mock_connect.return_value.__enter__.return_value = mock_conn

        writer = db_writer.DbWriter(
            dbname="meterdb", dbuser="meteruser", dbtable="readings"
        )

        mock_connect.assert_called_with(dbname="meterdb", user="meteruser")

        msg = reader.read_file(SAMPLE_FILE)
        writer.write(msg)

        assert mock_cursor.execute.call_count >= 1
        # Check last call args
        call_args = mock_cursor.execute.call_args[0]
        params = call_args[1]
        assert params["meter_id"] == "6970631402394972"
        assert params["obis_version"] == "KFM_001"
        assert params["il1"] == 2.778
        assert params["uln1"] == 240.6
