"""Public Binance Spot OHLCV research feed. No credentials, no order placement."""
import json,time,urllib.request,threading,math
_CACHE={}; _LOCK=threading.Lock(); REFRESH_SECONDS=60
SYMBOLS={'btc': 'BTCUSDT', 'eth': 'ETHUSDT', 'sol': 'SOLUSDT', 'xrp': 'XRPUSDT', 'tao': 'TAOUSDT', 'ada': 'ADAUSDT', 'avax': 'AVAXUSDT', 'link': 'LINKUSDT', 'doge': 'DOGEUSDT', 'sui': 'SUIUSDT'}
def fetch(market):
    if market not in SYMBOLS: raise ValueError('Unknown crypto market')
    now=time.time()
    with _LOCK:
        old=_CACHE.get(market)
        if old and now-old['last_attempt']<REFRESH_SECONDS:return dict(old)
        result={'candles':old['candles'] if old else [],'last_attempt':now,'last_success':old.get('last_success') if old else None,'error':None}
        try:
            url='https://data-api.binance.vision/api/v3/klines?symbol='+SYMBOLS[market]+'&interval=5m&limit=600'
            req=urllib.request.Request(url,headers={'User-Agent':'TaurusLab/0.6 (research)'})
            with urllib.request.urlopen(req,timeout=12) as response: rows=json.load(response)
            bars=[]
            for r in rows:
                ts=int(r[0])//1000
                # Start time + interval must be in the past. Exclude incomplete candles.
                if ts+300>now:continue
                op,hi,lo,cl=map(float,r[1:5]);vol=float(r[5])
                if not all(math.isfinite(v) for v in (op,hi,lo,cl,vol)):continue
                if not lo<=min(op,cl)<=max(op,cl)<=hi:continue
                bars.append(dict(time=ts,open=op,high=hi,low=lo,close=cl,volume=vol))
            if len(bars)<75:raise ValueError('Too few complete candles')
            result.update(candles=bars,last_success=int(now))
        except Exception as ex:result['error']=str(ex)[:200]
        _CACHE[market]=result
        return dict(result)
