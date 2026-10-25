"""Best-effort delayed Yahoo research feed, never exchange-grade live data."""
import time
from datetime import timezone
from threading import Lock

_CACHE_5M={'candles':[], 'last_attempt':0., 'last_success':None,'error':'Noch nicht geladen'}
_CACHE_1M={'candles':[], 'last_attempt':0., 'last_success':None,'error':'Noch nicht geladen'}
_LOCK=Lock()
MIN_REFRESH_SECONDS_5M=300
MIN_REFRESH_SECONDS_1M=60


FUTURES={'nq':'NQ=F','mes':'ES=F','mgc':'GC=F'}
_FUTURES_CACHE={}

def _fetch(period, interval, cache, min_refresh, symbol='NQ=F'):
    now=time.time()
    with _LOCK:
        if now-cache['last_attempt']<min_refresh:
            return dict(cache)
        cache['last_attempt']=now
        try:
            import yfinance as yf
            frame=yf.Ticker(symbol).history(period=period,interval=interval,auto_adjust=False,prepost=True,timeout=12)
            if frame.empty:
                raise RuntimeError('Yahoo liefert aktuell keine Kerzen')
            items=[]
            step=60 if interval=='1m' else 300
            for idx,r in frame.iterrows():
                t=int(idx.to_pydatetime().astimezone(timezone.utc).timestamp())
                op,hi,lo,cl=(float(r[c]) for c in ('Open','High','Low','Close'))
                if not all(__import__('math').isfinite(v) for v in (op,hi,lo,cl)):
                    continue
                if not lo<=min(op,cl)<=max(op,cl)<=hi:
                    continue
                if t+step>now:
                    continue
                items.append({'time':t,'open':op,'high':hi,'low':lo,'close':cl,'volume':float(r['Volume']) if r['Volume']==r['Volume'] else 0})
            items.sort(key=lambda x:x['time'])
            if len(items)<75:
                raise RuntimeError(f'Nur {len(items)} vollständige Kerzen verfügbar')
            cache.update(candles=items[-2000:],last_success=int(now),error=None)
        except Exception as ex:
            cache['error']=str(ex)[:180]
        return dict(cache)


def fetch(force=False):
    return _fetch('5d','5m',_CACHE_5M,0 if force else MIN_REFRESH_SECONDS_5M)


def fetch_1m(force=False):
    return _fetch('7d','1m',_CACHE_1M,0 if force else MIN_REFRESH_SECONDS_1M)


def fetch_market(market,interval='5m',force=False):
    """Delayed proxy contracts: NQ=F -> MNQ, ES=F -> MES, GC=F -> MGC.
    Not an exchange-grade micro-futures feed; do not live-execute from it.
    """
    if market not in FUTURES:raise ValueError('Unsupported futures market')
    if interval not in ('1m','5m'):raise ValueError('Unsupported interval')
    cache=_FUTURES_CACHE.setdefault((market,interval),{'candles':[],'last_attempt':0.,'last_success':None,'error':'Noch nicht geladen'})
    return _fetch('7d' if interval=='1m' else '5d',interval,cache,
                  0 if force else (MIN_REFRESH_SECONDS_1M if interval=='1m' else MIN_REFRESH_SECONDS_5M),FUTURES[market])
