"""One-day immutable research export. Paper data only; no brokerage orders."""
import os
from datetime import date,datetime,time,timedelta,timezone
from zoneinfo import ZoneInfo

SWISS=ZoneInfo('Europe/Zurich')

def daily_snapshot(day):
    """One Swiss civil day, covering LAB/LUCID candles, checks, signals and trades.

    Trades overlapping a day are included even if opened on an earlier date.
    Return one JSON-serializable object; GitHub Actions stores it as .json.gz.
    """
    d=date.fromisoformat(day)
    if d>datetime.now(SWISS).date():
        raise ValueError('Date must not be in the future')
    start=int(datetime.combine(d,time.min,SWISS).timestamp())
    end=int(datetime.combine(d+timedelta(days=1),time.min,SWISS).timestamp())
    from paper_engine import conn,TEST_VERSION,STRATEGY_SOURCE_HASH,RISK,DATABASE_URL
    from lucid_executor import VERSION,SELECTED,setup
    with conn() as db:
        setup(db)
        def rows(table,where,params):
            return [dict(x) for x in db.execute('SELECT * FROM '+table+' WHERE '+where,params).fetchall()]
        # Include all orders touching the day, including carried overnight positions.
        overlap='(signal_time>=? AND signal_time<?) OR (entry_time>=? AND entry_time<?) OR (exit_time>=? AND exit_time<?)'
        times=(start,end)*3
        trades=rows('trades',overlap,times)
        lucid_orders=rows('lucid_orders',overlap,times)
        account=[dict(x) for x in db.execute('SELECT * FROM lucid_account WHERE version=?',(VERSION,)).fetchall()]
        lab_signals=rows('signal_log','signal_time>=? AND signal_time<?',(start,end))
        scans=rows('strategy_scans','bar_time>=? AND bar_time<?',(start,end))
        candles=rows('market_candles','bar_time>=? AND bar_time<?',(start,end))
        progress=[dict(x) for x in db.execute('SELECT * FROM progress').fetchall()]
    return {'schema_version':1,'day_swiss':day,'day_start_utc':datetime.fromtimestamp(start,timezone.utc).isoformat(),
            'day_end_utc':datetime.fromtimestamp(end,timezone.utc).isoformat(),
            'generated_at_utc':datetime.now(timezone.utc).isoformat(),
            'code_commit':os.getenv('RENDER_GIT_COMMIT','unknown'),
            'strategy_source_hash':STRATEGY_SOURCE_HASH,
            'source':'Yahoo Finance delayed futures proxy (not real-time)',
            'mode':'paper-only, simulated fills',
            'persistence':'PostgreSQL' if DATABASE_URL else 'temporary SQLite',
            'lab':{'run_id':TEST_VERSION,'risk_usd':RISK,'trades':trades,'signal_events':lab_signals},
            'lucid':{'run_id':VERSION,'selected_strategies':list(SELECTED),
                     'account_snapshot_at_export':account,'orders':lucid_orders},
            'strategy_scans':scans,'market_candles':candles,'lab_progress':progress,
            'counts':{'lab_trades':len(trades),'lab_signals':len(lab_signals),'lucid_orders':len(lucid_orders),
                      'strategy_scans':len(scans),'candles':len(candles)}}
