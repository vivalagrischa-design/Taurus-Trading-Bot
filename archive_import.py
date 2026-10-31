"""One-time import of the daily GitHub research archives into PostgreSQL.

Why: until now TAURUS ran on a temporary SQLite file in /tmp that is wiped
on every Render deploy/restart. When DATABASE_URL is set for the first time,
the new PostgreSQL database starts empty. This module restores the current
V7 experiment from the archives on the `taurus-daily-archives` branch
(the same JSON files the daily GitHub Action writes) BEFORE the paper loop
starts, so no trade, signal, scan, candle or Lucid order is lost.

Safety:
- Runs only with DATABASE_URL (PostgreSQL). SQLite mode is untouched.
- Each archive day is imported once (table taurus_archive_imports).
- Upserts in chronological order: a later archive holds the newer state of
  the same trade (e.g. OPEN on day 1, CLOSED on day 2).
- paper_experiments.started_at is written BEFORE the normal schema init, so
  init_extra() does not start a new experiment, archive open trades or clear
  progress.
- Any failure is logged and the app keeps running.
"""
import gzip,json,logging,os,urllib.request

ARCHIVE_URL=os.environ.get('TAURUS_ARCHIVE_URL',
    'https://raw.githubusercontent.com/vivalagrischa-design/Taurus-Trading-Bot/taurus-daily-archives/archives/{year}/{day}.json.gz')
# Days of the current experiment taurus_v7_zero_start_20261026 that exist only
# in the archives (the SQLite file before the switch to PostgreSQL).
DEFAULT_DAYS=('2026-10-29','2026-10-30','2026-10-31')
# Experiment start of the SQLite run that produced these archives: the Render
# restart on 2026-10-29 07:31:29 UTC. With this value the dashboard shows the
# same totals as before the switch (749 closed LAB trades, -4,980.05 USD).
DEFAULT_STARTED_AT=int(os.environ.get('TAURUS_IMPORT_STARTED_AT','1793259089'))

PK={'trades':('id',),'signal_log':('id',),'lucid_orders':('id',),
    'strategy_scans':('system','run_id','market','strategy','timeframe','bar_time'),
    'market_candles':('system','run_id','market','timeframe','bar_time'),
    'trade_path':('trade_id','bar_time'),'progress':('market',),'lucid_account':('version',)}


def _days():
    raw=os.environ.get('TAURUS_IMPORT_DAYS','').strip()
    return tuple(d.strip() for d in raw.split(',') if d.strip()) if raw else DEFAULT_DAYS


def _download(day):
    url=ARCHIVE_URL.format(year=day[:4],day=day)
    with urllib.request.urlopen(url,timeout=60) as resp:
        data=json.loads(gzip.decompress(resp.read()))
    if data.get('schema_version')!=1 or data.get('day_swiss')!=day:
        raise ValueError('unexpected archive content for '+day)
    return data


def _columns(cur,table):
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name=%s",(table,))
    return {r[0] for r in cur.fetchall()}


def _upsert(cur,table,rows,update=True):
    if not rows:return 0
    cols=_columns(cur,table)
    keys=sorted({k for r in rows for k in r}&cols)
    pk=PK[table]
    if not keys or any(k not in keys for k in pk):return 0
    rest=[k for k in keys if k not in pk]
    action=('DO UPDATE SET '+','.join(f'{k}=EXCLUDED.{k}' for k in rest)) if (update and rest) else 'DO NOTHING'
    sql=(f'INSERT INTO {table} ({",".join(keys)}) VALUES ({",".join(["%s"]*len(keys))}) '
         f'ON CONFLICT ({",".join(pk)}) {action}')
    cur.executemany(sql,[tuple(r.get(k) for k in keys) for r in rows])
    return len(rows)


def run():
    database_url=os.environ.get('DATABASE_URL','')
    if not database_url:
        return {'skipped':'no DATABASE_URL'}
    try:
        return _run(database_url)
    except Exception as exc:
        logging.exception('TAURUS archive import failed')
        return {'error':str(exc)[:300]}


def _run(database_url):
    import psycopg
    from paper_engine import TEST_VERSION
    report={}
    # 1) Experiment marker first: prevents init_extra() from starting a new experiment.
    with psycopg.connect(database_url,connect_timeout=12) as pg:
        pg.execute('CREATE TABLE IF NOT EXISTS taurus_archive_imports(day TEXT PRIMARY KEY,imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),counts TEXT)')
        pg.execute('CREATE TABLE IF NOT EXISTS paper_experiments(version TEXT PRIMARY KEY, started_at BIGINT NOT NULL)')
        done={r[0] for r in pg.execute('SELECT day FROM taurus_archive_imports').fetchall()}
        todo=[d for d in _days() if d not in done]
        if not todo:
            return {'skipped':'all archive days already imported'}
        pg.execute('INSERT INTO paper_experiments(version,started_at) VALUES(%s,%s) ON CONFLICT(version) DO NOTHING',
                   (TEST_VERSION,DEFAULT_STARTED_AT))
    # 2) Normal schema creation (LAB + Lucid tables) through the app's own code.
    from paper_engine import conn
    from lucid_executor import setup
    with conn() as db:
        setup(db)
    # 3) Import archives oldest first.
    archives=[]
    for day in sorted(todo):
        archives.append((day,_download(day)))
    with psycopg.connect(database_url,connect_timeout=12) as pg:
        with pg.cursor() as cur:
            for day,a in archives:
                counts={
                  'trades':_upsert(cur,'trades',a['lab']['trades']),
                  'signal_log':_upsert(cur,'signal_log',a['lab']['signal_events']),
                  'lucid_orders':_upsert(cur,'lucid_orders',a['lucid']['orders']),
                  'strategy_scans':_upsert(cur,'strategy_scans',a['strategy_scans'],update=False),
                  'market_candles':_upsert(cur,'market_candles',a['market_candles'],update=False),
                  'trade_path':_upsert(cur,'trade_path',a['trade_path'],update=False)}
                report[day]=counts
            # Latest state only: progress watermarks and Lucid account.
            last=archives[-1][1]
            report['progress']=_upsert(cur,'progress',last.get('lab_progress') or [])
            report['lucid_account']=_upsert(cur,'lucid_account',last['lucid'].get('account_snapshot_at_export') or [])
            for day,_ in archives:
                cur.execute('INSERT INTO taurus_archive_imports(day,counts) VALUES(%s,%s) ON CONFLICT(day) DO NOTHING',
                            (day,json.dumps(report.get(day))))
        pg.commit()
    logging.warning('TAURUS archive import finished: %s',report)
    return report


if __name__=='__main__':
    print(run())
