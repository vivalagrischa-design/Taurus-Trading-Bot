"""TAURUS paper-only deterministic execution engine. No broker connections/orders.
Signal bar close -> next bar OPEN. Stops take priority on ambiguous OHLC bars.
State persisted in SQLite/PostgreSQL. Single process required.
"""
import os,sqlite3,threading,math
from strategies import evaluate

DB=os.environ.get('TAURUS_DB_PATH','/tmp/taurus_paper.db')
DATABASE_URL=os.environ.get('DATABASE_URL','')
RISK=200.0
MAX_NOTIONAL=float(os.environ.get('TAURUS_MAX_NOTIONAL_USD','5000'))
FEE_RATE=float(os.environ.get('TAURUS_PAPER_FEE_RATE','0.001'))
SLIPPAGE=float(os.environ.get('TAURUS_PAPER_SLIPPAGE','0.0002'))
MARKETS=tuple(__import__('crypto_feed').SYMBOLS)+('nq',)
ACTIVE_5M=('omar','rsi_ema','ema20','orb','rev_exhaustion','rev_engulfing','rev_pinbar','rev_bounce')
ACTIVE_1M=('opening_drop','opening_reversal')
ACTIVE_EXTREMES=('bb_rsi_short','bb_rsi_long')
ALL_STRATS=ACTIVE_5M+ACTIVE_1M+ACTIVE_EXTREMES
_LOCK=threading.RLock()


class PgConnection:
    def __init__(self):
        import psycopg
        from psycopg.rows import dict_row
        self.db=psycopg.connect(DATABASE_URL,row_factory=dict_row,connect_timeout=12)
    def execute(self,sql,params=()):
        if sql.startswith('PRAGMA '):
            return self.db.execute('SELECT 1')
        sql=sql.replace('?', '%s')
        if 'INSERT OR IGNORE INTO trades' in sql:
            sql=sql.replace('INSERT OR IGNORE INTO trades','INSERT INTO trades')+' ON CONFLICT (id) DO NOTHING'
        return self.db.execute(sql,params)
    def __enter__(self): return self
    def __exit__(self,t,v,tb):
        if t:self.db.rollback()
        else:self.db.commit()
        self.db.close()
    def commit(self): self.db.commit()


def conn():
    if DATABASE_URL:
        db=PgConnection(); init_tables(db); db.commit(); return db
    parent=os.path.dirname(DB)
    if parent: os.makedirs(parent,exist_ok=True)
    db=sqlite3.connect(DB,timeout=20)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS progress(market TEXT PRIMARY KEY,last_bar INTEGER NOT NULL)')
    db.execute('''CREATE TABLE IF NOT EXISTS trades(
       id TEXT PRIMARY KEY,market TEXT,strategy TEXT,side TEXT,signal_time INTEGER,
       entry_time INTEGER,exit_time INTEGER,entry REAL,stop REAL,tp REAL,qty REAL,
       risk_plan REAL,cost_estimate REAL,exit REAL,pnl REAL,exit_reason TEXT,status TEXT,
       signal_entry REAL,signal_stop REAL,signal_tp REAL, timeframe TEXT)''')
    init_extra(db); db.commit(); return db


def init_tables(db):
    db.execute('CREATE TABLE IF NOT EXISTS progress(market TEXT PRIMARY KEY,last_bar BIGINT NOT NULL)')
    db.execute('''CREATE TABLE IF NOT EXISTS trades(
       id TEXT PRIMARY KEY,market TEXT,strategy TEXT,side TEXT,signal_time BIGINT,
       entry_time BIGINT,exit_time BIGINT,entry DOUBLE PRECISION,stop DOUBLE PRECISION,tp DOUBLE PRECISION,qty DOUBLE PRECISION,
       risk_plan DOUBLE PRECISION,cost_estimate DOUBLE PRECISION,exit DOUBLE PRECISION,pnl DOUBLE PRECISION,exit_reason TEXT,status TEXT,
       signal_entry DOUBLE PRECISION,signal_stop DOUBLE PRECISION,signal_tp DOUBLE PRECISION, timeframe TEXT)''')
    init_extra(db)


def init_extra(db):
    # Idempotent additive migrations, including PostgreSQL.
    cols={'mfe_usd':'DOUBLE PRECISION','mae_usd':'DOUBLE PRECISION',
          'bb_position':'TEXT','bb_percent_b':'DOUBLE PRECISION',
          'entry_rsi':'DOUBLE PRECISION','entry_bar_time':'BIGINT',
          'initial_stop':'DOUBLE PRECISION','trail_updates':'INTEGER'}
    for name,sqltype in cols.items():
        if isinstance(db,PgConnection):
            db.execute('ALTER TABLE trades ADD COLUMN IF NOT EXISTS '+name+' '+sqltype)
        else:
            known={r['name'] for r in db.execute('PRAGMA table_info(trades)').fetchall()}
            if name not in known:db.execute('ALTER TABLE trades ADD COLUMN '+name+' '+sqltype)
    db.execute('''CREATE TABLE IF NOT EXISTS signal_log(id TEXT PRIMARY KEY,market TEXT,strategy TEXT,side TEXT,signal_time BIGINT,decision TEXT,reason TEXT)''')
    db.execute('CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy,market,signal_time)')


def record_signal(db,trade_id,market,strategy,sig,decision,reason):
    db.execute('INSERT INTO signal_log(id,market,strategy,side,signal_time,decision,reason) VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',
      (trade_id,market,strategy,sig['side'],int(sig['time']),decision,reason))


def _slipped(price,side,is_entry):
    buy=(side=='LONG')==is_entry
    return price*(1+SLIPPAGE if buy else 1-SLIPPAGE)


def _signals_for_last_5m(market,bars5m,bars1m=None):
    tiles=evaluate(bars5m,bars1m=bars1m,market=market)
    out=[]
    for st in tiles:
        if st['id'] not in ACTIVE_5M: continue
        for sig in st['signals']:
            if sig['time']==bars5m[-1]['time']:
                out.append((st['id'],sig))
    return out


def _signals_for_last_1m(market,bars1m,bars5m):
    tiles=evaluate(bars5m,bars1m=bars1m,market=market)
    out=[]
    for st in tiles:
        if st['id'] not in ACTIVE_1M: continue
        for sig in st['signals']:
            if sig['time']==bars1m[-1]['time']:
                out.append((st['id'],sig))
    return out


def _signals_for_last_extremes(market,bars1m,bars5m):
    from bb_rsi import build
    return [(st['id'],sig) for st in build(bars1m) if st['id'] in ACTIVE_EXTREMES for sig in st['signals'] if sig['time']==bars1m[-1]['time']]


def _entry_indicators(history):
    """Indicators from completed bars available at the time of entry."""
    if len(history)<20:return ('INSUFFICIENT',None,None)
    closes=[float(b['close']) for b in history]
    sample=closes[-20:]; mean=sum(sample)/20
    sd=math.sqrt(sum((c-mean)**2 for c in sample)/20)
    price=closes[-1]; upper=mean+2*sd; lower=mean-2*sd
    pct=(price-lower)/(upper-lower) if upper>lower else 0.5
    position='ABOVE_UPPER' if price>upper else 'BELOW_LOWER' if price<lower else 'UPPER_HALF' if price>=mean else 'LOWER_HALF'
    if len(closes)<15:return (position,round(pct,4),None)
    gains=[max(0,closes[j]-closes[j-1]) for j in range(1,len(closes))]
    losses=[max(0,closes[j-1]-closes[j]) for j in range(1,len(closes))]
    avg_g=sum(gains[:14])/14;avg_l=sum(losses[:14])/14
    for j in range(14,len(gains)):
        avg_g=(avg_g*13+gains[j])/14;avg_l=(avg_l*13+losses[j])/14
    rsi=100 if avg_l==0 else 100-100/(1+avg_g/avg_l)
    return (position,round(pct,4),round(rsi,2))


def _open_pending(db,market,bar,history):
    pending=db.execute("SELECT * FROM trades WHERE market=? AND status='PENDING' AND signal_time<?",(market,bar['time'])).fetchall()
    for t in pending:
        side=t['side']; entry=_slipped(float(bar['open']),side,True); stop=float(t['signal_stop']); tp=float(t['signal_tp'])
        dist=(entry-stop if side=='LONG' else stop-entry)
        if dist<=0 or (side=='LONG' and entry>=tp) or (side=='SHORT' and entry<=tp):
            db.execute("UPDATE trades SET status='CANCELLED',exit_reason='GAP_INVALID' WHERE id=?",(t['id'],)); continue
        if market=='nq':
            risk_per_unit=abs(entry-stop)*2+3.0+2*entry*SLIPPAGE*2
            qty=math.floor(RISK/max(risk_per_unit,0.0001))
            fees_est=qty*3.0
        else:
            risk_per_unit=dist+entry*FEE_RATE+stop*FEE_RATE+entry*SLIPPAGE+stop*SLIPPAGE
            qty=min(RISK/max(risk_per_unit,0.0000001),MAX_NOTIONAL/max(entry,0.0000001))
            qty=math.floor(qty*1e6)/1e6
            fees_est=qty*(entry+stop)*FEE_RATE
        risk_plan=qty*risk_per_unit
        if qty<=0 or risk_plan>RISK+1e-5:
            db.execute("UPDATE trades SET status='CANCELLED',exit_reason='RISK_LIMIT' WHERE id=?",(t['id'],)); continue
        bbpos,pct,rsi=_entry_indicators(history)
        db.execute("UPDATE trades SET status='OPEN',entry_time=?,entry=?,stop=?,tp=?,qty=?,risk_plan=?,cost_estimate=?,bb_position=?,bb_percent_b=?,entry_rsi=?,entry_bar_time=?,initial_stop=?,mfe_usd=0,mae_usd=0,trail_updates=0 WHERE id=?",
                   (bar['time'],entry,stop,tp,qty,risk_plan,fees_est,bbpos,pct,rsi,bar['time'],stop,t['id']))


def _close_open(db,market,bar):
    rows=db.execute("SELECT * FROM trades WHERE market=? AND status='OPEN' AND entry_time<=?",(market,bar['time'])).fetchall()
    for t in rows:
        side=t['side']; stop=t['stop']; tp=t['tp']
        multiplier=2 if market=='nq' else 1
        direction=1 if side=='LONG' else -1
        favorable=(float(bar['high'])-float(t['entry'])) if side=='LONG' else (float(t['entry'])-float(bar['low']))
        adverse=(float(t['entry'])-float(bar['low'])) if side=='LONG' else (float(bar['high'])-float(t['entry']))
        fee_est=(float(t['cost_estimate'] or 0))
        mfe=max(float(t['mfe_usd'] or 0),favorable*float(t['qty'])*multiplier-fee_est)
        mae=min(float(t['mae_usd'] or 0),-adverse*float(t['qty'])*multiplier-fee_est)
        db.execute('UPDATE trades SET mfe_usd=?,mae_usd=? WHERE id=?',(round(mfe,4),round(mae,4),t['id']))
        stop_hit=(bar['low']<=stop if side=='LONG' else bar['high']>=stop)
        tp_hit=(bar['high']>=tp if side=='LONG' else bar['low']<=tp)
        # Profit targets are reference levels, not automatic exits.
        # The initial stop always applies for the ENTIRE current candle.
        # A trailing adjustment is committed only AFTER its candle closes;
        # it is effective from the next candle (no same-bar lookahead).
        tp_hit=False
        if not stop_hit:
            initial_r=abs(float(t['entry'])-float(t['signal_stop']))
            if initial_r>0:
                direction=1 if side=='LONG' else -1
                favorable_close=(float(bar['close'])-float(t['entry']))*direction
                # Arm at +1R on a confirmed close, then follow the close by 1R.
                if favorable_close>=initial_r:
                    candidate=float(bar['close'])-direction*initial_r
                    new_stop=max(stop,candidate) if side=='LONG' else min(stop,candidate)
                    if new_stop!=stop:
                        db.execute('UPDATE trades SET stop=?,trail_updates=COALESCE(trail_updates,0)+1 WHERE id=?',(new_stop,t['id']))
        if not(stop_hit or tp_hit): continue
        if stop_hit:
            raw=min(stop,float(bar['open'])) if side=='LONG' else max(stop,float(bar['open']))
            reason='SL'
        else:
            raw=tp; reason='TP'
        exit_price=_slipped(raw,side,False)
        gross=(exit_price-t['entry'])*t['qty']*(1 if side=='LONG' else -1)*(2 if market=='nq' else 1)
        fees=(t['qty']*3.0 if market=='nq' else (t['entry']+exit_price)*t['qty']*FEE_RATE)
        pnl=gross-fees
        db.execute("UPDATE trades SET status='CLOSED',exit_time=?,exit=?,pnl=?,exit_reason=? WHERE id=?",
                   (bar['time'],exit_price,round(pnl,4),reason,t['id']))


def _progress_key(market, suffix='5m'):
    return market if suffix=='5m' else f'{market}:{suffix}'


def _advance_generic(market,bars,signal_lookup,suffix='5m'):
    if market not in MARKETS or not bars:
        return {'processed':0,'reason':'unsupported/no data'}
    bars=sorted(bars,key=lambda b:b['time']); last=int(bars[-1]['time']); step=60 if suffix in ('1m','extremes') else 300
    key=_progress_key(market,suffix)
    with _LOCK:
        with conn() as db:
            row=db.execute('SELECT last_bar FROM progress WHERE market=?',(key,)).fetchone()
            if row is None:
                db.execute('INSERT INTO progress VALUES (?,?)',(key,last))
                return {'processed':0,'reason':'first observation; no historical paper fills'}
            last_seen=int(row['last_bar'])
            if last<last_seen: return {'processed':0,'reason':'data older than watermark'}
            pending=[(i,b) for i,b in enumerate(bars) if b['time']>last_seen]
            if not pending: return {'processed':0,'reason':'no new complete candle'}
            if pending[0][1]['time']>last_seen+step:
                db.execute("UPDATE trades SET status='UNKNOWN',exit_reason='DATA_GAP' WHERE market=? AND status IN ('OPEN','PENDING')",(market,))
                db.execute('UPDATE progress SET last_bar=? WHERE market=?',(last,key))
                return {'processed':0,'reason':'data gap; open trades marked UNKNOWN'}
            count=0
            warmup=75 if suffix=='5m' else 60
            for i,b in pending:
                if i<warmup:
                    db.execute('UPDATE progress SET last_bar=? WHERE market=?',(int(b['time']),key)); continue
                _open_pending(db,market,b,bars[:i])
                _close_open(db,market,b)
                for strategy,sig in signal_lookup(i):
                    if sig['side'] not in ('LONG','SHORT'): continue
                    trade_id=f'{market}:{strategy}:{sig["time"]}:{sig["side"]}'
                    exists=db.execute("SELECT 1 FROM trades WHERE market=? AND strategy=? AND status IN ('PENDING','OPEN')",(market,strategy)).fetchone()
                    if exists:
                        record_signal(db,trade_id,market,strategy,sig,'SKIPPED','POSITION_ALREADY_ACTIVE')
                        continue
                    record_signal(db,trade_id,market,strategy,sig,'PENDING','NEXT_BAR_OPEN')
                    db.execute('''INSERT OR IGNORE INTO trades(id,market,strategy,side,signal_time,status,signal_entry,signal_stop,signal_tp,timeframe)
                                  VALUES(?,?,?,?,?,'PENDING',?,?,?,?)''',
                               (trade_id,market,strategy,sig['side'],int(sig['time']),float(sig['entry']),float(sig['stop']),float(sig['tp']),sig.get('timeframe','5m')))
                db.execute('UPDATE progress SET last_bar=? WHERE market=?',(int(b['time']),key))
                count+=1
            return {'processed':count,'reason':'updated'}


def advance(market,bars5m):
    return _advance_generic(market,bars5m,lambda i:_signals_for_last_5m(market,bars5m[:i+1]),'5m')


def advance_opening(market,bars1m,bars5m):
    if market!='nq' or not bars1m or not bars5m:
        return {'processed':0,'reason':'opening strategies only for nq with 1m feed'}
    return _advance_generic(market,bars1m,lambda i:_signals_for_last_1m(market,bars1m[:i+1],bars5m),'1m')


def advance_extremes(market,bars1m,bars5m):
    return _advance_generic(market,bars1m,lambda i:_signals_for_last_extremes(market,bars1m[:i+1],bars5m),'extremes')


def summary(market=None):
    with _LOCK:
        with conn() as db:
            sql='SELECT * FROM trades'; params=[]
            if market in MARKETS:
                sql+=' WHERE market=?'; params=[market]
            sql+=' ORDER BY signal_time DESC LIMIT 700'
            trades=[dict(t) for t in db.execute(sql,params)]
            aggregate={}
            for strategy in ALL_STRATS:
                rows=[t for t in trades if t['strategy']==strategy]
                closed=[t for t in rows if t['status']=='CLOSED' and t.get('pnl') is not None]
                aggregate[strategy]={
                    'open':sum(t['status']=='OPEN' for t in rows),
                    'pending':sum(t['status']=='PENDING' for t in rows),
                    'closed':len(closed),
                    'wins':sum((t['pnl'] or 0)>0 for t in closed),
                    'losses':sum((t['pnl'] or 0)<0 for t in closed),
                    'pnl':round(sum(t['pnl'] or 0 for t in closed),2)
                }
            last={r['market']:r['last_bar'] for r in db.execute('SELECT market,last_bar FROM progress').fetchall()}
            events=[dict(r) for r in db.execute('SELECT * FROM signal_log ORDER BY signal_time DESC LIMIT 1000').fetchall()]
            return {'events':events,'trades':trades,'summary':aggregate,'last_processed':last,'risk_usd':RISK,
                    'paper_only':True,'persistence':'PostgreSQL' if DATABASE_URL else DB,'markets':list(MARKETS)}
