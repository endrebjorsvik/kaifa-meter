import dataclasses
import logging
from typing import Any

import psycopg as pg
from psycopg import sql

from kaifa_meter import decoder

logger = logging.getLogger(__name__)

type MeterRow = dict[str, Any]


def init_table(table: str, cursor: pg.Cursor[Any], query: sql.Composed) -> None:
    """Check if table exists, and create it if missing."""
    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM pg_tables WHERE tablename = %s);", (table,)
    )
    row = cursor.fetchone()
    exists = row[0] if row else False
    if not exists:
        logger.info(f"Creating table {table}.")
        cursor.execute(query)
    else:
        logger.info(f"Table {table} already exists.")


def init_db(dbname: str, dbuser: str, dbtable: str) -> None:
    """Initialise database table schema for storing meter readings."""
    table = sql.SQL(
        """CREATE TABLE IF NOT EXISTS {} (
            id serial primary key,
            savetime timestamptz,
            meter_ts timestamp,
            obis_version text,
            meter_id text,
            meter_type text,
            items_count integer,
            pwr_act_pos double precision,
            pwr_act_neg double precision,
            pwr_react_pos double precision,
            pwr_react_neg double precision,
            il1 double precision,
            il2 double precision,
            il3 double precision,
            uln1 double precision,
            uln2 double precision,
            uln3 double precision,
            meter_ts2 timestamp,
            energy_act_pos double precision,
            energy_act_neg double precision,
            energy_react_pos double precision,
            energy_react_neg double precision
        );"""
    ).format(sql.Identifier(dbtable))

    with pg.connect(dbname=dbname, user=dbuser) as conn, conn.cursor() as cur:
        init_table(dbtable, cur, table)


@dataclasses.dataclass(slots=True)
class DbWriter:
    dbname: str
    dbuser: str
    dbtable: str

    def __post_init__(self) -> None:
        init_db(self.dbname, self.dbuser, self.dbtable)

    def write(self, msg: decoder.DecodedFrame) -> None:
        """Write decoded meter frame to PostgreSQL table."""
        d: MeterRow = {
            "meter_ts": msg.get("meter_ts"),
            "obis_version": msg.data.get("obis_version"),
            "meter_id": msg.data.get("meter_id"),
            "meter_type": msg.data.get("meter_type"),
            "items_count": msg.get("items_count"),
            "pwr_act_pos": msg.data.get("pwr_act_pos"),
            "pwr_act_neg": msg.data.get("pwr_act_neg"),
            "pwr_react_pos": msg.data.get("pwr_react_pos"),
            "pwr_react_neg": msg.data.get("pwr_react_neg"),
            "il1": msg.data_iv.get("IL1"),
            "il2": msg.data_iv.get("IL2"),
            "il3": msg.data_iv.get("IL3"),
            "uln1": msg.data_iv.get("ULN1"),
            "uln2": msg.data_iv.get("ULN2"),
            "uln3": msg.data_iv.get("ULN3"),
            "meter_ts2": msg.data_energy.get("meter_ts"),
            "energy_act_pos": msg.data_energy.get("act_pos"),
            "energy_act_neg": msg.data_energy.get("act_neg"),
            "energy_react_pos": msg.data_energy.get("react_pos"),
            "energy_react_neg": msg.data_energy.get("react_neg"),
        }
        q = sql.SQL(
            """INSERT INTO {} (
                savetime, meter_ts, obis_version, meter_id, meter_type,
                items_count, pwr_act_pos, pwr_act_neg, pwr_react_pos,
                pwr_react_neg, il1, il2, il3, uln1, uln2, uln3, meter_ts2,
                energy_act_pos, energy_act_neg, energy_react_pos, energy_react_neg
            ) VALUES (
                NOW(), %(meter_ts)s, %(obis_version)s, %(meter_id)s,
                %(meter_type)s, %(items_count)s, %(pwr_act_pos)s, %(pwr_act_neg)s,
                %(pwr_react_pos)s, %(pwr_react_neg)s, %(il1)s, %(il2)s, %(il3)s,
                %(uln1)s, %(uln2)s, %(uln3)s, %(meter_ts2)s, %(energy_act_pos)s,
                %(energy_act_neg)s, %(energy_react_pos)s, %(energy_react_neg)s
            );"""
        ).format(sql.Identifier(self.dbtable))

        with (
            pg.connect(dbname=self.dbname, user=self.dbuser) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(q, d)
