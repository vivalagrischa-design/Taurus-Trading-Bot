import csv,io,os
from fastapi import FastAPI,File,HTTPException,UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from engine import assess,demo_candles
from strategies import evaluate

app=FastAPI(title='Omar Live – Dashboard',version='0.1.0')
app.mount('/static',StaticFiles(directory='static'),name='static')
# Demo / uploaded bars are in process memory: no durable storage, no claimed realtime feed.
DATA={'mode':'DEMO','candles':demo_candles()}

@app.get('/')
def index():return FileResponse('static/index.html')

@app.get('/health')
def health():return {'ok':True,'mode':DATA['mode']}

@app.get('/api/state')
def state():
    out=assess(DATA['candles']);out['mode']=DATA['mode'];out['market']='NQ / MNQ';out['realtime']=False
    return out

@app.get('/api/strategies')
def strategies():
    return {'mode':DATA['mode'],'realtime':False,'market':'NQ / MNQ','candles':DATA['candles'][-210:],'strategies':evaluate(DATA['candles']),'last_bar_time':DATA['candles'][-1]['time']}

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
