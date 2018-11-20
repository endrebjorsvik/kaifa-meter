import logging
import psycopg2 as pg
from kaifa_meter.decoder import get_field


def init_table(table, cursor, query):
    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM pg_tables WHERE tablename = %s);",
        (table,)
    )
    if not cursor.fetchall()[0][0]:
        logging.info("Creating table {}.".format(table))
        cursor.execute(query)
    else:
        logging.info("Table {} already exists.".format(table))


def init_db(dbname, dbuser, dbtable):
    table = (
        "CREATE TABLE {} ( "
        "id serial primary key, "
        "savetime timestamptz, "
        "meter_ts timestamp, "
        "obis_version text, "
        "meter_id text, "
        "meter_type text, "
        "items_count integer, "
        "pwr_act_pos double precision, "
        "pwr_act_neg double precision, "
        "pwr_react_pos double precision, "
        "pwr_react_neg double precision, "
        "il1 double precision, "
        "il2 double precision, "
        "il3 double precision, "
        "uln1 double precision, "
        "uln2 double precision, "
        "uln3 double precision, "
        "meter_ts2 timestamp, "
        "energy_act_pos double precision, "
        "energy_act_neg double precision, "
        "energy_react_pos double precision, "
        "energy_react_neg double precision);".format(dbtable)
    )
    with pg.connect(dbname=dbname, user=dbname) as conn:
        with conn.cursor() as cur:
            init_table(dbtable, cur, table)


class DbWriter:
    def __init__(self, dbname, dbuser, dbtable):
        self.dbname = dbname
        self.dbuser = dbuser
        self.dbtable = dbtable
        init_db(self.dbname, self.dbuser, self.dbtable)

    def write(self, msg):
        d = {
            "meter_ts": get_field(msg, "meter_ts"),
            "obis_version": get_field(msg.data, "obis_version"),
            "meter_id": get_field(msg.data, "meter_id"),
            "meter_type": get_field(msg.data, "meter_type"),
            "items_count": get_field(msg.data, "items_count"),
            "pwr_act_pos": get_field(msg.data, "pwr_act_pos"),
            "pwr_act_neg": get_field(msg.data, "pwr_act_neg"),
            "pwr_react_pos": get_field(msg.data, "pwr_react_pos"),
            "pwr_react_neg": get_field(msg.data, "pwr_react_neg"),
            "il1": get_field(msg.data, "IL1"),
            "il2": get_field(msg.data, "IL2"),
            "il3": get_field(msg.data, "IL3"),
            "uln1": get_field(msg.data, "ULN1"),
            "uln2": get_field(msg.data, "ULN2"),
            "uln3": get_field(msg.data, "ULN3"),
            "meter_ts2": get_field(msg.data, "meter_ts"),
            "energy_act_pos": get_field(msg.data, "energy_act_pos"),
            "energy_act_neg": get_field(msg.data, "energy_act_neg"),
            "energy_react_pos": get_field(msg.data, "energy_react_pos"),
            "energy_react_neg": get_field(msg.data, "energy_react_neg"),
        }
        q = ("INSERT INTO {} ( "
             "savetime, meter_ts, obis_version, meter_id, meter_type, "
             "items_count, pwr_act_pos, pwr_act_neg, pwr_react_pos, "
             "pwr_react_neg, il1, il2, il3, uln1, uln2, uln3, meter_ts2, "
             "energy_act_pos, energy_act_neg, energy_react_pos, energy_react_neg ) "
             "VALUES( "
             "NOW(), %(meter_ts)s, %(obis_version)s, %(meter_id)s, "
             "%(meter_type)s, %(items_count)s, %(pwr_act_pos)s, %(pwr_act_neg)s, "
             "%(pwr_react_pos)s, %(pwr_react_neg)s, %(il1)s, %(il2)s, %(il3)s, "
             "%(uln1)s, %(uln2)s, %(uln3)s, %(meter_ts2)s, %(energy_act_pos)s, "
             "%(energy_act_neg)s, %(energy_react_pos)s, %(energy_react_neg)s"
             ");".format(self.dbtable))
        with pg.connect(dbname=self.dbname, user=self.dbuser) as conn:
            with conn.cursor() as cur:
                cur.execute(q, d)
