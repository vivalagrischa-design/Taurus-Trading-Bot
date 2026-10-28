"""TAURUS paper-only deterministic execution engine. No broker connections/orders.
Signal bar close -> next bar OPEN. Stops take priority on ambiguous OHLC bars.
State persisted in SQLite/PostgreSQL. Single process required.
"""
import os,sqlite3,threading,math,time
from strategies import evaluate
from setup_quality import score_signal

DB=os.environ.get('TAURUS_DB_PATH','/tmp/taurus_paper.db')
DATABASE_URL=os.environ.get('DATABASE_URL','')
RISK=200.0
MAX_NOTIONAL=float(os.environ.get('TAURUS_MAX_NOTIONAL_USD','5000'))
FEE_RATE=float(os.environ.get('TAURUS_PAPER_FEE_RATE','0.001'))
SLIPPAGE=float(os.environ.get('TAURUS_PAPER_SLIPPAGE','0.0002'))
FUTURES={'nq':(2.0,1.0),'mes':(5.0,1.0),'mgc':(10.0,1.60)}
FUTURES_TICK={'nq':0.25,'mes':0.25,'mgc':0.10}
FUTURES_SLIP_TICKS=float(os.environ.get('TAURUS_FUTURES_SLIP_TICKS','1'))  # multiplier, Lucid per-contract round-trip commission
MARKETS=tuple(FUTURES)
ACTIVE_5M=('omar','omar_v2_volume_retest','rsi_ema','ema20','orb','rev_exhaustion','rev_engulfing','rev_pinbar','rev_bounce','rev_exhaustion_confirmed','rev_engulfing_confirmed','rev_pinbar_confirmed','rev_bounce_confirmed','trend_pullback','trend_pullback_mtf','bb_rsi_scale','rosi_frankfurt','rosi_london','rosi_new_york')
ACTIVE_1M=('opening_drop','opening_reversal')
ACTIVE_EXTREMES=('bb_only_short','bb_only_long','bb_rsi_short','bb_rsi_long','bb_reversal_short','bb_reversal_long')
ALL_STRATS=ACTIVE_5M+ACTIVE_1M+ACTIVE_EXTREMES
TEST_VERSION='taurus_v7_zero_start_20261026'
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
          'initial_stop':'DOUBLE PRECISION','trail_updates':'INTEGER',
          'stop_net_estimate':'DOUBLE PRECISION','break_even_stop':'DOUBLE PRECISION','scale_legs':'INTEGER','scale_pending':'INTEGER','last_leg_price':'DOUBLE PRECISION','entry_context':'TEXT','exit_context':'TEXT','strategy_version':'TEXT'}
    for name,sqltype in cols.items():
        if isinstance(db,PgConnection):
            db.execute('ALTER TABLE trades ADD COLUMN IF NOT EXISTS '+name+' '+sqltype)
        else:
            known={r['name'] for r in db.execute('PRAGMA table_info(trades)').fetchall()}
            if name not in known:db.execute('ALTER TABLE trades ADD COLUMN '+name+' '+sqltype)
    db.execute('''CREATE TABLE IF NOT EXISTS signal_log(id TEXT PRIMARY KEY,market TEXT,strategy TEXT,side TEXT,signal_time BIGINT,decision TEXT,reason TEXT)''')
    db.execute('CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy,market,signal_time)')
    # Preserve previous test history; initialize this experiment only once.
    db.execute('CREATE TABLE IF NOT EXISTS paper_experiments(version TEXT PRIMARY KEY, started_at BIGINT NOT NULL)')
    existing=db.execute('SELECT started_at FROM paper_experiments WHERE version=?',(TEST_VERSION,)).fetchone()
    if existing is None:
        started=int(time.time())
        db.execute('INSERT INTO paper_experiments(version,started_at) VALUES(?,?)',(TEST_VERSION,started))
        # Previous version must never continue into new experiment.
        db.execute("UPDATE trades SET status='ARCHIVED',exit_reason='PREVIOUS_EXPERIMENT' WHERE status IN ('OPEN','PENDING')")
        db.execute('DELETE FROM progress')



def record_signal(db,trade_id,market,strategy,sig,decision,reason):
    db.execute('INSERT INTO signal_log(id,market,strategy,side,signal_time,decision,reason) VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',
      (trade_id,market,strategy,sig['side'],int(sig['time']),decision,reason))


def _slipped(price,side,is_entry,market=None):
    buy=(side=='LONG')==is_entry
    slip=FUTURES_TICK[market]*FUTURES_SLIP_TICKS if market in FUTURES_TICK else price*SLIPPAGE
    return price+(slip if buy else -slip)


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


def _engine_strategies(suffix):
    return ACTIVE_5M if suffix=='5m' else ACTIVE_1M if suffix=='1m' else ACTIVE_EXTREMES


def _net_target_price(entry,side,target_usd,qty,market):
    """Raw TP trigger including exit slippage and both fees."""
    if market in FUTURES:
        multiplier,commission=FUTURES[market]
        exit_price=entry+(1 if side=='LONG' else -1)*(target_usd/max(qty*multiplier,1e-9)+commission/multiplier)
    elif side=='LONG':
        exit_price=(target_usd/max(qty,1e-9)+entry*(1+FEE_RATE))/(1-FEE_RATE)
    else:
        exit_price=(entry*(1-FEE_RATE)-target_usd/max(qty,1e-9))/(1+FEE_RATE)
    return (exit_price+(FUTURES_TICK[market]*FUTURES_SLIP_TICKS if side=='LONG' else -FUTURES_TICK[market]*FUTURES_SLIP_TICKS)) if market in FUTURES_TICK else exit_price/(1-SLIPPAGE if side=='LONG' else 1+SLIPPAGE)


def _add_scaled_legs(db,market,bar,suffix):
    if suffix!='5m' or market in FUTURES:return
    open_price=float(bar['open'])
    rows=db.execute("SELECT * FROM trades WHERE market=? AND strategy='bb_rsi_scale' AND status='OPEN' AND scale_pending=1",(market,)).fetchall()
    for t in rows:
        side=t['side'];old_qty=float(t['qty']);old_entry=float(t['entry'])
        stop=float(t['initial_stop'])
        # Do not increase a losing position when the current open has already breached SL.
        if (side=='SHORT' and open_price>=stop) or (side=='LONG' and open_price<=stop):
            db.execute("UPDATE trades SET scale_pending=0 WHERE id=?",(t['id'],));continue
        fill=_slipped(open_price,side,True,market)
        previous=float(t['last_leg_price'] or old_entry)
        if (side=='SHORT' and fill<=previous) or (side=='LONG' and fill>=previous):
            db.execute("UPDATE trades SET scale_pending=0 WHERE id=?",(t['id'],));continue
        budget=max(0,MAX_NOTIONAL/3)
        add_qty=math.floor(min(budget/max(fill,1e-12),max(0,MAX_NOTIONAL-old_qty*old_entry)/max(fill,1e-12))*1e6)/1e6
        if add_qty<=0:
            db.execute("UPDATE trades SET scale_pending=0 WHERE id=?",(t['id'],));continue
        new_qty=old_qty+add_qty;average=(old_entry*old_qty+fill*add_qty)/new_qty
        possible_loss=_estimated_net_at_stop({'side':side,'entry':average,'qty':new_qty},stop,market)
        if possible_loss < -RISK:
            db.execute("UPDATE trades SET scale_pending=0 WHERE id=?",(t['id'],));continue
        tp=_net_target_price(average,side,25,new_qty,market)
        db.execute("UPDATE trades SET qty=?,entry=?,tp=?,cost_estimate=?,risk_plan=?,scale_legs=COALESCE(scale_legs,1)+1,scale_pending=0,last_leg_price=?,break_even_stop=?,stop_net_estimate=? WHERE id=?",
            (new_qty,average,tp,(average+stop)*new_qty*FEE_RATE,abs(min(0,possible_loss)),fill,
             _net_break_even_stop(average,side,market),possible_loss,t['id']))


def _open_pending(db,market,bar,history,suffix):
    strategies=_engine_strategies(suffix)
    marks=','.join('?' for _ in strategies)
    pending=db.execute("SELECT * FROM trades WHERE market=? AND status='PENDING' AND signal_time<? AND strategy IN ("+marks+")",
                       (market,bar['time'],*strategies)).fetchall()
    for t in pending:
        side=t['side']; entry=_slipped(float(bar['open']),side,True,market); stop=float(t['signal_stop']); tp=float(t['signal_tp'])
        dist=(entry-stop if side=='LONG' else stop-entry)
        if dist<=0 or (side=='LONG' and entry>=tp) or (side=='SHORT' and entry<=tp):
            db.execute("UPDATE trades SET status='CANCELLED',exit_reason='GAP_INVALID' WHERE id=?",(t['id'],)); continue
        if t['strategy']=='bb_rsi_scale' and market in FUTURES:
            db.execute("UPDATE trades SET status='CANCELLED',exit_reason='CRYPTO_RESEARCH_ONLY' WHERE id=?",(t['id'],));continue
        if market in FUTURES:
            multiplier,commission=FUTURES[market]
            risk_per_unit=abs(entry-stop)*multiplier+commission+FUTURES_TICK[market]*FUTURES_SLIP_TICKS*multiplier
            qty=math.floor(RISK/max(risk_per_unit,0.0001))
            # TAURUS LAB is an independent strategy research ledger.
            # Its quantity is set ONLY by the 200 USD per-trade risk budget.
            # Lucid contract/account limits belong exclusively to lucid_executor.py.
            fees_est=qty*commission
        else:
            risk_per_unit=dist+entry*FEE_RATE+stop*FEE_RATE+entry*SLIPPAGE+stop*SLIPPAGE
            qty=min(RISK/max(risk_per_unit,0.0000001),MAX_NOTIONAL/max(entry,0.0000001))
            qty=math.floor(qty*1e6)/1e6
            fees_est=qty*(entry+stop)*FEE_RATE
        if t['strategy']=='bb_rsi_scale':
            qty=min(qty,math.floor((MAX_NOTIONAL/3)/max(entry,1e-12)*1e6)/1e6)
            tp=_net_target_price(entry,side,25,qty,market) if qty>0 else tp
        if qty>0 and _estimated_net_at_stop({'side':side,'entry':entry,'qty':qty},tp,market)<=0:
            db.execute("UPDATE trades SET status='CANCELLED',exit_reason='TP_NOT_PROFITABLE_NET' WHERE id=?",(t['id'],));continue
        risk_plan=qty*risk_per_unit
        if qty<=0 or risk_plan>RISK+1e-5:
            db.execute("UPDATE trades SET status='CANCELLED',exit_reason='RISK_LIMIT' WHERE id=?",(t['id'],)); continue
        bbpos,pct,rsi=_entry_indicators(history)
        db.execute("UPDATE trades SET status='OPEN',entry_time=?,entry=?,stop=?,tp=?,qty=?,risk_plan=?,cost_estimate=?,bb_position=?,bb_percent_b=?,entry_rsi=?,entry_bar_time=?,initial_stop=?,mfe_usd=0,mae_usd=0,trail_updates=0,stop_net_estimate=?,break_even_stop=?,scale_legs=?,scale_pending=0,last_leg_price=? WHERE id=?",
                   (bar['time'],entry,stop,tp,qty,risk_plan,fees_est,bbpos,pct,rsi,bar['time'],stop,
                    _estimated_net_at_stop({'side':side,'entry':entry,'qty':qty},stop,market),
                    _net_break_even_stop(entry,side,market),1 if t['strategy']=='bb_rsi_scale' else None,entry,t['id']))


def _net_break_even_stop(entry,side,market):
    """Raw stop trigger required for estimated zero net P/L after fill slippage and fees."""
    if market in FUTURES:
        multiplier,commission=FUTURES[market]
        actual_exit=entry+(commission/multiplier if side=='LONG' else -commission/multiplier)
    elif side=='LONG':
        actual_exit=entry*(1+FEE_RATE)/(1-FEE_RATE)
    else:
        actual_exit=entry*(1-FEE_RATE)/(1+FEE_RATE)
    return (actual_exit+(FUTURES_TICK[market]*FUTURES_SLIP_TICKS if side=='LONG' else -FUTURES_TICK[market]*FUTURES_SLIP_TICKS)) if market in FUTURES_TICK else actual_exit/(1-SLIPPAGE if side=='LONG' else 1+SLIPPAGE)


def _estimated_net_at_stop(trade,stop,market):
    """Conservative projected exit P/L: exit-side slippage plus both fees."""
    side=trade['side']; entry=float(trade['entry']); qty=float(trade['qty'])
    exit_price=_slipped(float(stop),side,False,market)
    gross=(exit_price-entry)*qty*(1 if side=='LONG' else -1)*(FUTURES[market][0] if market in FUTURES else 1)
    fees=(qty*FUTURES[market][1] if market in FUTURES else (entry+exit_price)*qty*FEE_RATE)
    return round(gross-fees,4)


def _close_open(db,market,bar,suffix):
    strategies=_engine_strategies(suffix)
    marks=','.join('?' for _ in strategies)
    rows=db.execute("SELECT * FROM trades WHERE market=? AND status='OPEN' AND entry_time<=? AND strategy IN ("+marks+")",
                    (market,bar['time'],*strategies)).fetchall()
    for t in rows:
        side=t['side']; stop=t['stop']; tp=t['tp']
        multiplier=FUTURES[market][0] if market in FUTURES else 1
        direction=1 if side=='LONG' else -1
        favorable=(float(bar['high'])-float(t['entry'])) if side=='LONG' else (float(t['entry'])-float(bar['low']))
        adverse=(float(t['entry'])-float(bar['low'])) if side=='LONG' else (float(bar['high'])-float(t['entry']))
        fee_est=(float(t['cost_estimate'] or 0))
        mfe=max(float(t['mfe_usd'] or 0),favorable*float(t['qty'])*multiplier-fee_est)
        mae=min(float(t['mae_usd'] or 0),-adverse*float(t['qty'])*multiplier-fee_est)
        db.execute('UPDATE trades SET mfe_usd=?,mae_usd=? WHERE id=?',(round(mfe,4),round(mae,4),t['id']))
        stop_hit=(bar['low']<=stop if side=='LONG' else bar['high']>=stop)
        tp_hit=(bar['high']>=tp if side=='LONG' else bar['low']<=tp)
        # TP is an actual exit. If both SL and TP are touched within one OHLC
        # candle, conservatively assume SL first (intrabar order unknown).
        # Trailing decisions use the finished candle and take effect next bar.
        if not (stop_hit or tp_hit) and t['strategy'] not in ('bb_rsi_scale','rev_bounce'):
            initial_r=abs(float(t['entry'])-float(t['signal_stop']))
            if initial_r>0:
                direction=1 if side=='LONG' else -1
                favorable_close=(float(bar['close'])-float(t['entry']))*direction
                # Arm at +1R on a confirmed close, then follow the close by 1R.
                if favorable_close>=initial_r:
                    candidate=float(bar['close'])-direction*initial_r
                    new_stop=max(stop,candidate) if side=='LONG' else min(stop,candidate)
                    if new_stop!=stop:
                        net_at_stop=_estimated_net_at_stop(t,new_stop,market)
                        # Preserve protective trailing even before break-even;
                        # distinguish gross locked profit from after-cost result.
                        db.execute('UPDATE trades SET stop=?,stop_net_estimate=?,trail_updates=COALESCE(trail_updates,0)+1 WHERE id=?',(new_stop,net_at_stop,t['id']))
        if not(stop_hit or tp_hit) and t['strategy']=='bb_rsi_scale' and int(t['scale_legs'] or 1)<3 and not int(t['scale_pending'] or 0):
            last_leg=float(t['last_leg_price'] or t['entry'])
            adverse_against_last=(float(bar['close'])/last_leg-1) if side=='SHORT' else (1-float(bar['close'])/last_leg)
            if adverse_against_last>=.003:
                db.execute("UPDATE trades SET scale_pending=1 WHERE id=?",(t['id'],))
        if not(stop_hit or tp_hit): continue
        if stop_hit:
            raw=min(stop,float(bar['open'])) if side=='LONG' else max(stop,float(bar['open']))
            reason='SL'
        else:
            raw=tp; reason='TP'
        exit_price=_slipped(raw,side,False,market)
        gross=(exit_price-t['entry'])*t['qty']*(1 if side=='LONG' else -1)*multiplier
        fees=(t['qty']*FUTURES[market][1] if market in FUTURES else (t['entry']+exit_price)*t['qty']*FEE_RATE)
        pnl=gross-fees
        db.execute("UPDATE trades SET status='CLOSED',exit_time=?,exit=?,pnl=?,exit_reason=? WHERE id=?",
                   (bar['time'],exit_price,round(pnl,4),reason,t['id']))


def _progress_key(market, suffix='5m'):
    return market if suffix=='5m' else f'{market}:{suffix}'


def _trade_context(bars,stamp):
    prior=[b for b in bars if int(b['time'])<=int(stamp)]
    tail=prior[-25:]
    if not tail:return {'phase':'unknown','reason':'no_prior_candles','candles':[]}
    closes=[float(b['close']) for b in tail]
    change=(closes[-1]-closes[max(0,len(closes)-13)])/closes[max(0,len(closes)-13)] if len(closes)>=13 else None
    phase=('up' if change is not None and change>0.001 else 'down' if change is not None and change<-.001 else 'sideways' if change is not None else 'unknown')
    last=tail[-1]; rng=max(float(last['high'])-float(last['low']),1e-12); body=abs(float(last['close'])-float(last['open']))
    return {'phase':phase,'return_60m':change,'last_candle':{'time':int(last['time']),'open':float(last['open']),'high':float(last['high']),'low':float(last['low']),'close':float(last['close']),'volume':float(last.get('volume',0) or 0),'direction':'up' if last['close']>last['open'] else 'down' if last['close']<last['open'] else 'flat','body_range_ratio':body/rng,'upper_wick_ratio':(float(last['high'])-max(float(last['open']),float(last['close'])))/rng,'lower_wick_ratio':(min(float(last['open']),float(last['close']))-float(last['low']))/rng},'candles':[{'time':int(b['time']),'open':float(b['open']),'high':float(b['high']),'low':float(b['low']),'close':float(b['close']),'volume':float(b.get('volume',0) or 0)} for b in tail]}


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
                db.execute("UPDATE trades SET status='UNKNOWN',exit_reason='DATA_GAP' WHERE market=? AND strategy IN ("+','.join('?' for _ in _engine_strategies(suffix))+") AND status IN ('OPEN','PENDING')",(market,*_engine_strategies(suffix)))
                db.execute('UPDATE progress SET last_bar=? WHERE market=?',(last,key))
                return {'processed':0,'reason':'data gap; open trades marked UNKNOWN'}
            count=0
            warmup=75 if suffix=='5m' else 60
            for i,b in pending:
                if i<warmup:
                    db.execute('UPDATE progress SET last_bar=? WHERE market=?',(int(b['time']),key)); continue
                _add_scaled_legs(db,market,b,suffix)
                _open_pending(db,market,b,bars[:i],suffix)
                _close_open(db,market,b,suffix)
                for strategy,sig in signal_lookup(i):
                    if sig['side'] not in ('LONG','SHORT'): continue
                    trade_id=f'{market}:{strategy}:{sig["time"]}:{sig["side"]}'
                    quality=score_signal(sig,bars[:i+1])
                    score_note='QUALITY_'+str(quality['score'])+'_'+quality['grade']
                    exists=db.execute("SELECT 1 FROM trades WHERE market=? AND strategy=? AND status IN ('PENDING','OPEN')",(market,strategy)).fetchone()
                    if exists:
                        record_signal(db,trade_id,market,strategy,sig,'SKIPPED','POSITION_ALREADY_ACTIVE '+score_note)
                        continue
                    record_signal(db,trade_id,market,strategy,sig,'PENDING','NEXT_BAR_OPEN '+score_note)
                    context_bars=bars[max(0,i-24):i+1]
                    signal_context=_trade_context(context_bars,int(sig['time']))
                    db.execute('''INSERT OR IGNORE INTO trades(id,market,strategy,side,signal_time,status,signal_entry,signal_stop,signal_tp,timeframe,entry_context,strategy_version)
                                  VALUES(?,?,?,?,?,'PENDING',?,?,?,?,?,?)''',
                               (trade_id,market,strategy,sig['side'],int(sig['time']),float(sig['entry']),float(sig['stop']),float(sig['tp']),sig.get('timeframe','5m'),json.dumps(signal_context,separators=(',',':')),str(sig.get('version','unknown'))))
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
            exp=db.execute('SELECT started_at FROM paper_experiments WHERE version=?',(TEST_VERSION,)).fetchone()
            started=int(exp['started_at']) if exp else int(time.time())
            sql='SELECT * FROM trades WHERE signal_time>=?'; params=[started]
            if market in MARKETS:
                sql+=' AND market=?'; params.append(market)
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
            events=[dict(r) for r in db.execute('SELECT * FROM signal_log WHERE signal_time>=? ORDER BY signal_time DESC LIMIT 1000',(started,)).fetchall()]
            return {'events':events,'trades':trades,'summary':aggregate,'last_processed':last,'risk_usd':RISK,
                    'paper_only':True,'experiment':TEST_VERSION,'experiment_started_at':started,'persistence':'PostgreSQL' if DATABASE_URL else DB,'markets':list(MARKETS)}
