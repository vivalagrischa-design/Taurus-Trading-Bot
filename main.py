import csv,io,threading,logging
from contextlib import asynccontextmanager
from paper_engine import advance, advance_opening, advance_extremes, summary
from fastapi import FastAPI,File,HTTPException,UploadFile,Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from engine import assess,demo_candles
from strategies import evaluate
from yahoo_feed import fetch as fetch_yahoo, fetch_1m as fetch_yahoo_1m
from crypto_feed import fetch as fetch_crypto, fetch_1m as fetch_crypto_1m, SYMBOLS

_stop=threading.Event()
last_poll={market:None for market in list(SYMBOLS)+['nq','nq_opening']}


def paper_loop():
    while not _stop.is_set():
        for market in SYMBOLS:
            try:
                data=fetch_crypto(market)
                if data['candles'] and not data['error']:
                    last_poll[market]=advance(market,data['candles'])
                    one=fetch_crypto_1m(market)
                    if one['candles'] and not one['error']:
                        last_poll[market+'_1m']=advance_extremes(market,one['candles'],data['candles'])
                else:
                    last_poll[market]={'processed':0,'reason':data.get('error') or 'no data'}
            except Exception as exc:
                logging.exception('Paper poll failed for %s',market)
                last_poll[market]={'processed':0,'reason':str(exc)[:180]}
        try:
            f5=fetch_yahoo()
            if f5['candles'] and not f5['error']:
                last_poll['nq']=advance('nq',f5['candles'])
            else:
                last_poll['nq']={'processed':0,'reason':f5.get('error') or 'no data'}
            f1=fetch_yahoo_1m()
            if f5['candles'] and f1['candles'] and not f1['error']:
                last_poll['nq_opening']=advance_opening('nq',f1['candles'],f5['candles'])
                last_poll['nq_bb']=advance_extremes('nq',f1['candles'],f5['candles'])
            else:
                last_poll['nq_opening']={'processed':0,'reason':f1.get('error') or 'no 1m data'}
        except Exception as exc:
            logging.exception('Nasdaq delayed paper poll failed')
            last_poll['nq']={'processed':0,'reason':str(exc)[:180]}
            last_poll['nq_opening']={'processed':0,'reason':str(exc)[:180]}
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
    if market in SYMBOLS:
        f=fetch_crypto(market)
        bars=f['candles']
        f1=fetch_crypto_1m(market)
        bars1m=f1['candles']
        name=SYMBOLS[market].replace('USDT','/USDT')
        mode='BINANCE SPOT · 5M/1M'
        provider='Binance Spot public klines'
        error=' · '.join(x for x in (f['error'],f1['error']) if x) or None
        updated=f['last_success']
        market_type='crypto'
    else:
        f=fetch_yahoo()
        f1=fetch_yahoo_1m()
        bars=f['candles']
        bars1m=f1['candles']
        name='Nasdaq NQ=F'
        mode='YAHOO (VERZÖGERT) · 5M/1M' if bars else 'KEINE YAHOO-DATEN'
        provider='Yahoo Finance NQ=F'
        error=' · '.join(x for x in [f.get('error'), f1.get('error')] if x) or None
        updated=max([x for x in [f.get('last_success'), f1.get('last_success')] if x] or [None])
        market_type='futures'
    if not bars:
        return {'mode':mode,'realtime':False,'market':name,'candles_5m':[],'candles_1m':bars1m,
                'strategies':[],'last_bar_time':None,'feed_error':error,
                'last_fetch_time':updated,'provider':provider,'market_type':market_type}
    evaluated=evaluate(bars,bars1m=bars1m,market=market)
    if market!='nq':
        for st in evaluated:
            if st['id'] in ('opening_drop','opening_reversal','orb'):
                continue
            for sig in st['signals']:
                sig['mnq_contracts']=None
                sig['status']='KRYPTO · HISTORISCHER TESTKANDIDAT'
    return {'mode':mode,'realtime':False,'market':name,'candles_5m':bars[-420:],'candles_1m':bars1m[-900:] if bars1m else [],
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
    if market != 'all' and market not in SYMBOLS and market != 'nq':
        raise HTTPException(400, detail='Unbekannter Markt')
    result=summary(None if market=='all' else market)
    result['poll']=last_poll if market=='all' else last_poll.get(market)
    result['delayed_nq']=(market=='nq' or market=='all')
    return result
