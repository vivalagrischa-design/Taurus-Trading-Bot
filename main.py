import csv,io,threading,logging
from contextlib import asynccontextmanager
from paper_engine import advance, advance_opening, advance_extremes, summary
from fastapi import FastAPI,File,HTTPException,UploadFile,Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from engine import assess,demo_candles
from strategies import evaluate
from yahoo_feed import fetch as fetch_yahoo, fetch_1m as fetch_yahoo_1m, fetch_market, FUTURES
from crypto_feed import fetch as fetch_crypto, fetch_1m as fetch_crypto_1m, SYMBOLS

_stop=threading.Event()
last_poll={market:None for market in FUTURES}


def paper_loop():
    while not _stop.is_set():
        for market in FUTURES:
            try:
                five=fetch_market(market,'5m')
                if not five['candles'] or five['error']:
                    last_poll[market]={'processed':0,'reason':five.get('error') or 'no 5m data'}
                    continue
                last_poll[market]=advance(market,five['candles'])
                from lucid_executor import advance as lucid_advance
                last_poll[market+'_lucid']=lucid_advance(market,five['candles'])
                one=fetch_market(market,'1m')
                if one['candles'] and not one['error']:
                    last_poll[market+'_lucid_1m']=lucid_advance(market,one['candles'],interval='1m')
                    last_poll[market+'_bb']=advance_extremes(market,one['candles'],five['candles'])
                    if market=='nq':
                        last_poll[market+'_opening']=advance_opening(market,one['candles'],five['candles'])
            except Exception as exc:
                logging.exception('Futures paper poll failed for %s',market)
                last_poll[market]={'processed':0,'reason':str(exc)[:180]}
        _stop.wait(60)


@asynccontextmanager
async def lifespan(app):
    thread=threading.Thread(target=paper_loop,daemon=True,name='taurus-paper-only')
    thread.start()
    yield
    _stop.set()
    thread.join(timeout=3)


app=FastAPI(title='Taurus Trading Lab',version='1.2.0',lifespan=lifespan)
app.mount('/static',StaticFiles(directory='static'),name='static')
DATA={'mode':'DEMO','candles':demo_candles()}


def snapshot():
    if DATA['mode']=='YAHOO':
        f=fetch_yahoo()
        if f['candles']:
            return f['candles'], 'YAHOO (VERZÖGERT)', f['error'], f['last_success']
        return demo_candles(), 'DEMO (YAHOO NICHT VERFÜGBAR)', f['error'], f['last_success']
    return DATA['candles'],DATA['mode'],None,None


@app.get('/')
def index():
    return FileResponse('static/index.html')


@app.get('/health')
def health():
    return {'ok':True,'mode':DATA['mode']}


@app.get('/api/state')
def state():
    bars,mode,error,updated=snapshot()
    out=assess(bars)
    out['mode']=mode;out['market']='NQ / MNQ';out['realtime']=False;out['feed_error']=error
    return out


@app.get('/api/strategies')
def strategies(market: str = Query('nq', pattern=r'^[a-z0-9]{1,16}$')):
    bars1m=[]
    if market not in FUTURES:
        raise HTTPException(status_code=400,detail='TAURUS handelt im aktuellen Test nur Lucid-Futures: nq, mes, mgc')
    f=fetch_market(market,'5m')
    f1=fetch_market(market,'1m')
    bars=f['candles']
    bars1m=f1['candles']
    symbol={'nq':'MNQ (Nasdaq)','mes':'MES (S&P 500)','mgc':'MGC (Gold)'}[market]
    name=symbol+' · Yahoo-Proxy '+FUTURES[market]
    mode='LUCID FUTURES PAPER · VERZÖGERTE DATEN'
    provider='Yahoo Finance '+FUTURES[market]+' (Proxy, nicht Lucid-Livefeed)'
    error=' · '.join(x for x in [f.get('error'),f1.get('error')] if x) or None
    updated=max([x for x in [f.get('last_success'),f1.get('last_success')] if x] or [None])
    market_type='futures'
    if not bars:
        return {'mode':mode,'realtime':False,'market':name,'candles_5m':[],'candles_1m':bars1m,
                'strategies':[],'last_bar_time':None,'feed_error':error,
                'last_fetch_time':updated,'provider':provider,'market_type':market_type}
    evaluated=evaluate(bars,bars1m=bars1m,market=market)
    if False:
        for st in evaluated:
            if st['id'] in ('opening_drop','opening_reversal','orb'):
                continue
            for sig in st['signals']:
                sig['mnq_contracts']=None
                sig['status']='KRYPTO · HISTORISCHER TESTKANDIDAT'
    return {'mode':mode,'realtime':False,'market':name,'candles_5m':bars[-2000:],'candles_1m':bars1m[-900:] if bars1m else [],
            'strategies':evaluated,'last_bar_time':bars[-1]['time'], 'last_bar_time_1m':bars1m[-1]['time'] if bars1m else None,
            'feed_error':error,'last_fetch_time':updated,'provider':provider,
            'market_type':market_type}


@app.post('/api/upload')
async def upload(file:UploadFile=File(...)):
    raw=await file.read(3_000_001)
    if len(raw)>3_000_000:raise HTTPException(413,'Datei zu gross (max. 3 MB)')
    try:
        rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
        if len(rows)>5000:raise ValueError('Maximal 5000 Kerzen')
        items=[]
        for r in rows:
            t=(r.get('time') or r.get('timestamp') or r.get('datetime') or '').strip()
            if not t:raise ValueError('Spalte time/timestamp/datetime fehlt')
            if t.isdigit():stamp=int(t);stamp=stamp//1000 if stamp>10**11 else stamp
            else:
                from datetime import datetime,timezone
                dt=datetime.fromisoformat(t.replace('Z','+00:00'))
                if dt.tzinfo is None:raise ValueError('Zeitstempel benötigen UTC-Zone, z.B. +00:00')
                stamp=int(dt.astimezone(timezone.utc).timestamp())
            b={'time':stamp}
            for k in ('open','high','low','close'):
                b[k]=float(r[k])
            b['volume']=float(r.get('volume') or 0)
            if not (b['low']<=min(b['open'],b['close'])<=max(b['open'],b['close'])<=b['high']):raise ValueError('Ungültige OHLC-Zeile')
            items.append(b)
        items.sort(key=lambda x:x['time'])
        if len(items)<75 or any(items[i]['time']==items[i-1]['time'] for i in range(1,len(items))):raise ValueError('Mindestens 75 eindeutige 5M-Kerzen erforderlich')
        if any(items[i]['time']-items[i-1]['time']!=300 for i in range(1,len(items))):raise ValueError('Demo benötigt lückenlose 5-Minuten-Kerzen (keine Overnight-/Wochenend-Lücken)')
        DATA.update(mode='CSV-IMPORT',candles=items)
        return {'ok':True,'count':len(items)}
    except (ValueError,KeyError,UnicodeError) as ex:
        raise HTTPException(400,detail=str(ex))


@app.post('/api/demo')
def reset_demo():
    DATA.update(mode='DEMO',candles=demo_candles())
    return {'ok':True}


@app.post('/api/yahoo')
def select_yahoo():
    DATA['mode']='YAHOO'
    return {'ok':True,'message':'Yahoo-Modus aktiviert; verzögerte Forschungsdaten'}


@app.get('/api/paper')
def paper(market: str = 'all'):
    if market != 'all' and market not in FUTURES:
        raise HTTPException(400, detail='Unbekannter Markt')
    result=summary(None if market=='all' else market)
    result['poll']=last_poll if market=='all' else last_poll.get(market)
    result['delayed_nq']=(market=='nq' or market=='all')
    return result

@app.get('/api/lucid')
def lucid_status():
    from lucid_executor import status
    try:
        return status()
    except Exception as exc:
        logging.exception('Lucid status failed')
        raise HTTPException(503,'Lucid shadow database not available') from exc


@app.get('/lucid')
def lucid_page():
    from fastapi.responses import HTMLResponse
    return HTMLResponse("""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TAURUS Lucid</title><style>body{background:#0c1420;color:#e6edf6;font:16px system-ui;margin:0;padding:24px;max-width:1100px}a{color:#8bcaff}h1{font-size:30px}.box{background:#19283b;padding:18px;border-radius:12px;margin:14px 0;overflow:auto}.warn{color:#ffbc70}dl{display:grid;grid-template-columns:1fr 1fr;gap:10px}dt{color:#b0bdca}dd{margin:0;font-weight:bold}table{border-collapse:collapse;width:100%;min-width:850px}th,td{text-align:left;padding:9px;border-bottom:1px solid #35465c;white-space:nowrap}.pos{color:#38d3a1}.neg{color:#ff7185}.muted{color:#b0bdca}</style></head><body><a href="/">← TAURUS Lab</a> · <a href="/static/results.html">Strategie-Grafiken</a><h1>TAURUS Lucid · 25K</h1><div class="box"><h2 class="warn">Eigenständiges Lucid-Papertrading</h2><p>Verzögerte Marktdaten, simulierte Ausführung, keine Echtgeldorders.</p></div><div class="box"><h2>Kontoregeln</h2><dl><dt>Startkapital</dt><dd>25’000 USD</dd><dt>Gewinnziel</dt><dd>1’250 USD</dd><dt>Maximalverlust</dt><dd>1’000 USD</dd><dt>Micro-Kontrakte</dt><dd>20</dd><dt>Risikobudget je Trade</dt><dd>200 USD</dd><dt>Ausführung</dt><dd>Papertrading</dd></dl></div><div class="box"><h2>Kontostand</h2><p id="balance">Lade…</p><p id="counts"></p></div><div class="box"><h2>Lucid Trades</h2><p class="muted">Neueste Trades zuerst · Signale, offene, geschlossene und stornierte Trades.</p><table><thead><tr><th>Zeit Signal</th><th>Markt</th><th>Strategie</th><th>Richtung</th><th>Entry</th><th>Stop</th><th>Exit</th><th>Kontrakte</th><th>Status</th><th>P/L</th><th>Grund</th></tr></thead><tbody id="rows"></tbody></table></div><p><a href="/api/lucid">Status als JSON</a></p><script>const esc=x=>String(x??'—').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));function dt(t){return t?new Date(Number(t)*1000).toLocaleString('de-CH'):'—'}fetch('/api/lucid').then(r=>{if(!r.ok)throw Error('Status nicht verfügbar');return r.json()}).then(d=>{document.getElementById('balance').textContent='Kontostand: '+Number(d.balance).toFixed(2)+' USD · P/L: '+Number(d.realized_pnl).toFixed(2)+' USD · Handelssperre: '+(d.locked?'JA':'NEIN');document.getElementById('counts').textContent='Geschlossen: '+d.closed_trades+' · Offen: '+d.open_trades+' · Strategien: '+(d.selected_strategies||[]).join(', ');document.getElementById('rows').innerHTML=(d.trades||[]).map(t=>'<tr><td>'+dt(t.signal_time)+'</td><td>'+esc(t.market)+'</td><td>'+esc(t.strategy)+'</td><td>'+esc(t.side)+'</td><td>'+esc(t.entry)+'</td><td>'+esc(t.stop)+'</td><td>'+esc(t.exit_time?dt(t.exit_time):'—')+'</td><td>'+esc(t.qty)+'</td><td>'+esc(t.status)+'</td><td class="'+(Number(t.pnl)>=0?'pos':'neg')+'">'+(t.pnl==null?'—':Number(t.pnl).toFixed(2)+' USD')+'</td><td>'+esc(t.exit_reason)+'</td></tr>').join('')||'<tr><td colspan="11">Noch keine Lucid-Trades oder Signale gespeichert.</td></tr>'}).catch(e=>document.getElementById('balance').textContent=e.message)</script></body></html>""")
