"""Independent persistent Lucid 25K paper executor. No brokerage connectivity.

Processes only newly observed completed 5m candles; signals enter on the
following bar open. Intrabar SL wins ties. A single process is required.
"""
import math,threading,time,json
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from paper_engine import conn,FUTURES,FUTURES_TICK,FUTURES_SLIP_TICKS,_trade_context,_record_scans
from strategies import evaluate

LOCK=threading.RLock()
NY=ZoneInfo('America/New_York')
VERSION='lucid_independent_25k_v1'
START=25000.
SELECTED=('rev_engulfing','rev_bounce','trend_pullback','bb_only_short')
MAX_QTY=20
RISK=200.
DAY_STOP=400.

def setup(db):
    db.execute("""CREATE TABLE IF NOT EXISTS lucid_account(
       version TEXT PRIMARY KEY,balance DOUBLE PRECISION NOT NULL,
       peak DOUBLE PRECISION NOT NULL,floor DOUBLE PRECISION NOT NULL,
       session_day TEXT,session_start DOUBLE PRECISION,locked INTEGER NOT NULL DEFAULT 0,
       last_bar_nq BIGINT,last_bar_mes BIGINT,last_bar_mgc BIGINT,
        last_bar_1m_nq BIGINT,last_bar_1m_mes BIGINT,last_bar_1m_mgc BIGINT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS lucid_orders(
       id TEXT PRIMARY KEY,market TEXT,strategy TEXT,side TEXT,
       signal_time BIGINT,entry_time BIGINT,exit_time BIGINT,
       entry DOUBLE PRECISION,stop DOUBLE PRECISION,initial_stop DOUBLE PRECISION,tp DOUBLE PRECISION,
       qty INTEGER,status TEXT,pnl DOUBLE PRECISION,exit_reason TEXT,
        timeframe TEXT NOT NULL DEFAULT '5m',signal_context TEXT,entry_context TEXT,exit_context TEXT,strategy_version TEXT)""")
    # Additive migrations for existing Lucid accounts and paper orders.
    from paper_engine import PgConnection
    for col in ('last_bar_1m_nq','last_bar_1m_mes','last_bar_1m_mgc'):
        if isinstance(db,PgConnection):
            db.execute('ALTER TABLE lucid_account ADD COLUMN IF NOT EXISTS '+col+' BIGINT')
        elif col not in {r['name'] for r in db.execute('PRAGMA table_info(lucid_account)')}:
            db.execute('ALTER TABLE lucid_account ADD COLUMN '+col+' BIGINT')
    if isinstance(db,PgConnection):
        db.execute("ALTER TABLE lucid_orders ADD COLUMN IF NOT EXISTS timeframe TEXT NOT NULL DEFAULT '5m'")
    elif 'timeframe' not in {r['name'] for r in db.execute('PRAGMA table_info(lucid_orders)')}:
        db.execute("ALTER TABLE lucid_orders ADD COLUMN timeframe TEXT NOT NULL DEFAULT '5m'")
    if isinstance(db,PgConnection):
        db.execute('ALTER TABLE lucid_orders ADD COLUMN IF NOT EXISTS initial_stop DOUBLE PRECISION')
    elif 'initial_stop' not in {r['name'] for r in db.execute('PRAGMA table_info(lucid_orders)')}:
        db.execute('ALTER TABLE lucid_orders ADD COLUMN initial_stop DOUBLE PRECISION')
    for col in ('signal_context','entry_context','exit_context','strategy_version'):
        if isinstance(db,PgConnection):
            db.execute('ALTER TABLE lucid_orders ADD COLUMN IF NOT EXISTS '+col+' TEXT')
        elif col not in {r['name'] for r in db.execute('PRAGMA table_info(lucid_orders)')}:
            db.execute('ALTER TABLE lucid_orders ADD COLUMN '+col+' TEXT')
    db.execute("""INSERT INTO lucid_account(version,balance,peak,floor,session_start,locked)
       VALUES(?,?,?,?,?,0) ON CONFLICT(version) DO NOTHING""",(VERSION,START,START,START-1000,START))

def _slip(px,side,entry,market):
    buy=(side=='LONG')==entry
    return float(px)+(1 if buy else -1)*FUTURES_TICK[market]*FUTURES_SLIP_TICKS

def _session(db,acct,stamp):
    day=datetime.fromtimestamp(stamp,timezone.utc).astimezone(NY).date().isoformat()
    if acct['session_day']!=day:
        peak=max(float(acct['peak']),float(acct['balance']))
        floor=min(25100.,peak-1000.)
        locked=int(float(acct['balance'])<=floor)
        db.execute('UPDATE lucid_account SET session_day=?,session_start=balance,peak=?,floor=?,locked=? WHERE version=?',
                   (day,peak,floor,locked,VERSION))

def _close(db,trade,bar,history=None,timeframe='5m'):
    market=trade['market'];side=trade['side'];stop=float(trade['stop']);tp=float(trade['tp'])
    hit_sl=float(bar['low'])<=stop if side=='LONG' else float(bar['high'])>=stop
    hit_tp=float(bar['high'])>=tp if side=='LONG' else float(bar['low'])<=tp
    if not (hit_sl or hit_tp):
        initial_value=trade['initial_stop']
        initial_stop=float(initial_value if initial_value is not None else stop)
        initial_r=abs(float(trade['entry'])-initial_stop)
        favorable=(float(bar['close'])-float(trade['entry']))*(1 if side=='LONG' else -1)
        if trade['strategy']!='rev_bounce' and initial_r>0 and favorable>=initial_r:
            candidate=float(bar['close'])-(1 if side=='LONG' else -1)*initial_r
            stop=max(stop,candidate) if side=='LONG' else min(stop,candidate)
            db.execute('UPDATE lucid_orders SET stop=? WHERE id=?',(stop,trade['id']))
        return
    raw=(min(stop,float(bar['open'])) if side=='LONG' else max(stop,float(bar['open']))) if hit_sl else tp
    px=_slip(raw,side,False,market)
    mult,fee=FUTURES[market]
    pnl=round((px-float(trade['entry']))*(1 if side=='LONG' else -1)*mult*int(trade['qty'])-fee*int(trade['qty']),4)
    exit_context=json.dumps(_trade_context(history or [bar],int(bar['time']),timeframe),separators=(',',':'))
    db.execute("UPDATE lucid_orders SET status='CLOSED',exit_time=?,pnl=?,exit_reason=?,exit_context=? WHERE id=?",
               (bar['time'],pnl,'SL' if hit_sl else 'TP',exit_context,trade['id']))
    db.execute('UPDATE lucid_account SET balance=balance+? WHERE version=?',(pnl,VERSION))
    a=db.execute('SELECT * FROM lucid_account WHERE version=?',(VERSION,)).fetchone()
    if float(a['balance'])<=float(a['floor']) or float(a['session_start'])-float(a['balance'])>=DAY_STOP:
        db.execute('UPDATE lucid_account SET locked=1 WHERE version=?',(VERSION,))

def _open(db,trade,bar,history=None,timeframe='5m'):
    market=trade['market'];side=trade['side'];entry=_slip(bar['open'],side,True,market)
    stop=float(trade['stop']);tp=float(trade['tp'])
    if (side=='LONG' and (stop>=entry or tp<=entry)) or (side=='SHORT' and (stop<=entry or tp>=entry)):
        db.execute("UPDATE lucid_orders SET status='CANCELLED',exit_reason='INVALID_GAP' WHERE id=?",(trade['id'],));return
    a=db.execute('SELECT * FROM lucid_account WHERE version=?',(VERSION,)).fetchone()
    ny=datetime.fromtimestamp(int(bar['time']),timezone.utc).astimezone(NY)
    if int(a['locked']) or ny.weekday()==5 or (ny.weekday()==6 and ny.hour<18) or (ny.hour==16) or ny.hour==17:
        db.execute("UPDATE lucid_orders SET status='CANCELLED',exit_reason='ACCOUNT_OR_SESSION_LOCK' WHERE id=?",(trade['id'],));return
    active=db.execute("SELECT market,side,qty,entry,stop FROM lucid_orders WHERE status='OPEN'").fetchall()
    if any(t['market']==market and t['side']!=side for t in active):
        db.execute("UPDATE lucid_orders SET status='CANCELLED',exit_reason='OPPOSITE_POSITION' WHERE id=?",(trade['id'],));return
    mult,fee=FUTURES[market]
    risk_unit=abs(entry-stop)*mult+fee+FUTURES_TICK[market]*FUTURES_SLIP_TICKS*mult
    available=MAX_QTY-sum(int(t['qty']) for t in active)
    open_risk=sum(abs(float(t['entry'])-float(t['stop']))*FUTURES[t['market']][0]*int(t['qty']) for t in active)
    maxrisk=max(0,min(RISK,600-open_risk,float(a['balance'])-float(a['floor'])-open_risk))
    qty=min(available,int(maxrisk//risk_unit)) if risk_unit>0 else 0
    if qty<=0:
        db.execute("UPDATE lucid_orders SET status='CANCELLED',exit_reason='CAPACITY_OR_RISK' WHERE id=?",(trade['id'],));return
    entry_context=json.dumps(_trade_context(history or [],int(bar['time']),timeframe),separators=(',',':'))
    db.execute("UPDATE lucid_orders SET status='OPEN',entry_time=?,entry=?,qty=?,initial_stop=?,entry_context=? WHERE id=?",(bar['time'],entry,qty,stop,entry_context,trade['id']))

def advance(market,bars,interval='5m'):
    if market not in FUTURES or not bars or interval not in ('5m','1m'):
        return {'processed':0}
    bars=sorted(bars,key=lambda x:x['time'])
    col=('last_bar_'+market) if interval=='5m' else ('last_bar_1m_'+market)
    with LOCK:
        with conn() as db:
            setup(db)
            a=db.execute('SELECT * FROM lucid_account WHERE version=?',(VERSION,)).fetchone()
            if a[col] is None:
                db.execute('UPDATE lucid_account SET '+col+'=? WHERE version=?',(int(bars[-1]['time']),VERSION))
                return {'processed':0,'reason':'first observation; no historical fills'}
            last=int(a[col]); processed=0
            for i,bar in enumerate(bars):
                if int(bar['time'])<=last:continue
                _session(db,a,int(bar['time']))
                pending=db.execute("SELECT * FROM lucid_orders WHERE market=? AND timeframe=? AND status='PENDING' AND signal_time<? ORDER BY signal_time",(market,interval,bar['time'])).fetchall()
                for trade in pending:_open(db,trade,bar,bars[:i],interval)
                active=db.execute("SELECT * FROM lucid_orders WHERE market=? AND timeframe=? AND status='OPEN' AND entry_time<=?",(market,interval,bar['time'])).fetchall()
                for trade in active:_close(db,trade,bar,bars[:i+1],interval)
                # Only signals generated from data available at this completed bar.
                if i>=(75 if interval=='5m' else 320):
                    if interval=='5m':
                        tiles=evaluate(bars[:i+1],market=market)
                    else:
                        from bb_rsi import build as bb_build
                        tiles=bb_build(bars[max(0,i-450):i+1])
                    for tile in tiles:
                        if tile['id'] not in SELECTED:continue
                        if interval=='5m' and tile['id']=='bb_only_short':continue
                        if interval=='1m' and tile['id']!='bb_only_short':continue
                        for sig in tile.get('signals',[]):
                            if int(sig['time'])!=int(bar['time']):continue
                            side=sig['side'];stop=float(sig['stop']);tp=float(sig['tp'])
                            if side not in ('LONG','SHORT'):continue
                            ident=f"{VERSION}:{market}:{tile['id']}:{int(bar['time'])}:{side}"
                            db.execute("""INSERT INTO lucid_orders(id,market,strategy,side,signal_time,stop,tp,status,qty,timeframe,signal_context,strategy_version)
                               VALUES(?,?,?,?,?,?,?,'PENDING',0,?,?,?) ON CONFLICT(id) DO NOTHING""",
                               (ident,market,tile['id'],side,int(bar['time']),stop,tp,interval,json.dumps(_trade_context(bars[max(0,i-(240 if interval=='1m' else 48)):i+1],int(bar['time']),interval),separators=(',',':')),str(sig.get('version','unknown'))))
                    scan_allowed=tuple(x for x in SELECTED if not (interval=='5m' and x=='bb_only_short')) if interval=='5m' else ('bb_only_short',)
                    _record_scans(db,'lucid',VERSION,market,tiles,bar,interval,bars[:i+1],scan_allowed)
                db.execute('UPDATE lucid_account SET '+col+'=? WHERE version=?',(int(bar['time']),VERSION))
                a=db.execute('SELECT * FROM lucid_account WHERE version=?',(VERSION,)).fetchone()
                processed+=1
            return {'processed':processed}

def status():
    with LOCK:
        with conn() as db:
            setup(db)
            a=dict(db.execute('SELECT * FROM lucid_account WHERE version=?',(VERSION,)).fetchone())
            rows=[dict(x) for x in db.execute('SELECT * FROM lucid_orders ORDER BY signal_time DESC LIMIT 150')]
            return {'name':'TAURUS Lucid 25K','mode':'INDEPENDENT_PAPER','trading_active':True,
                    'real_orders':False,'execution_connected':True,'persistent_account_connected':True,
                    'starting_balance':START,'balance':round(float(a['balance']),2),
                    'realized_pnl':round(float(a['balance'])-START,2),
                    'floor':a['floor'],'locked':bool(a['locked']),
                    'selected_strategies':list(SELECTED),'open_trades':sum(x['status']=='OPEN' for x in rows),
                    'closed_trades':sum(x['status']=='CLOSED' for x in rows),
                    'trades':rows,'max_micro_contracts':MAX_QTY,'risk_per_trade':RISK,
                    'last_processed':{m:a['last_bar_'+m] for m in FUTURES},
                     'last_processed_1m':{m:a['last_bar_1m_'+m] for m in FUTURES},
                    'warning':'Independent delayed-data paper execution; not real-time, not broker-connected; fills are simulated.'}
