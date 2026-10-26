"""Persistent Lucid 25K shadow ledger, sourced from actual completed TAURUS paper fills.

Research-only. No brokerage orders. The source paper engine is not a separate
Lucid execution engine; its fills are mirrored with a conservative daily stop.
"""
import threading
from paper_engine import conn, TEST_VERSION

_LOCK=threading.RLock()
START=25000.0
MAX_LOSS=1000.0
DAILY_LIMIT=400.0

def _init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS lucid_shadow_ledger(
      trade_id TEXT PRIMARY KEY, experiment TEXT NOT NULL, market TEXT,
      strategy TEXT, exit_time BIGINT, pnl DOUBLE PRECISION NOT NULL,
      accepted INTEGER NOT NULL, reason TEXT NOT NULL)""")

def sync():
    """Idempotently account for newly closed V7 paper trades, chronologically."""
    with _LOCK:
        with conn() as db:
            _init(db)
            started=db.execute('SELECT started_at FROM paper_experiments WHERE version=?',(TEST_VERSION,)).fetchone()
            start=int(started['started_at']) if started else 0
            rows=db.execute("""SELECT id,market,strategy,exit_time,pnl FROM trades
                 WHERE status='CLOSED' AND exit_time>=? AND pnl IS NOT NULL
                 ORDER BY exit_time,id""",(start,)).fetchall()
            prior=db.execute('SELECT trade_id FROM lucid_shadow_ledger WHERE experiment=?',(TEST_VERSION,)).fetchall()
            known={r['trade_id'] for r in prior}
            existing=db.execute('SELECT exit_time,pnl,accepted FROM lucid_shadow_ledger WHERE experiment=? ORDER BY exit_time,trade_id',(TEST_VERSION,)).fetchall()
            balance=START
            day=None; day_start=START; locked=False; breached=False; peak=START; floor=START-MAX_LOSS
            for r in existing:
                t=int(r['exit_time'] or 0)//86400
                if t!=day:
                    if day is not None:
                        peak=max(peak,balance);floor=min(25100.0,peak-MAX_LOSS)
                    day=t;day_start=balance;locked=breached
                if r['accepted']:
                    balance+=float(r['pnl'])
                    if balance<=floor:breached=True;locked=True
                    if day_start-balance>=DAILY_LIMIT:locked=True
            for r in rows:
                if r['id'] in known:continue
                t=int(r['exit_time'] or 0)//86400
                if t!=day:
                    if day is not None:
                        peak=max(peak,balance);floor=min(25100.0,peak-MAX_LOSS)
                    day=t;day_start=balance;locked=breached
                accepted=0 if locked else 1
                reason='ACCOUNT_LOCKED' if locked else 'MIRRORED_PAPER_CLOSE'
                db.execute('INSERT INTO lucid_shadow_ledger(trade_id,experiment,market,strategy,exit_time,pnl,accepted,reason) VALUES(?,?,?,?,?,?,?,?)',
                    (r['id'],TEST_VERSION,r['market'],r['strategy'],r['exit_time'],float(r['pnl']),accepted,reason))
                if accepted:
                    balance+=float(r['pnl'])
                    if balance<=floor:breached=True;locked=True
                    if day_start-balance>=DAILY_LIMIT:locked=True
            return _report(db,start)

def _report(db,start):
    rows=db.execute('SELECT pnl,accepted,reason,market,strategy,exit_time FROM lucid_shadow_ledger WHERE experiment=? ORDER BY exit_time',(TEST_VERSION,)).fetchall()
    realized=sum(float(r['pnl']) for r in rows if r['accepted'])
    return {'name':'TAURUS Lucid 25K','mode':'PERSISTENT_SHADOW_PAPER',
            'execution_connected':False,'persistent_account_connected':True,
            'trading_active':False,'shadow_accounting_active':True,
            'starting_balance':START,'balance':round(START+realized,2),
            'realized_pnl':round(realized,2),'mirrored_closed_trades':sum(bool(r['accepted']) for r in rows),
            'rejected_after_lock':sum(not bool(r['accepted']) for r in rows),
            'profit_target':1250,'max_loss':MAX_LOSS,'max_micro_contracts':20,
            'risk_per_trade':200,'experiment':TEST_VERSION,'started_at':start,
            'warning':'Shadow ledger mirrors existing Lab paper fills, not independent Lucid entries. No real orders; not a validated Lucid evaluation.'}
