"""Best-effort delayed Yahoo research feed, never exchange-grade live data."""
import time
from datetime import datetime,timezone
from threading import Lock

_CACHE={'candles':[], 'last_attempt':0., 'last_success':None,'error':'Noch nicht geladen'}
_LOCK=Lock()
MIN_REFRESH_SECONDS=300

def fetch(force=False):
    now=time.time()
    with _LOCK:
        if now-_CACHE['last_attempt']<MIN_REFRESH_SECONDS:
            return dict(_CACHE)
        _CACHE['last_attempt']=now
        try:
            import yfinance as yf
            frame=yf.Ticker('NQ=F').history(period='5d',interval='5m',auto_adjust=False,prepost=True,timeout=12)
            if frame.empty:raise RuntimeError('Yahoo liefert aktuell keine Kerzen')
            items=[]
            for idx,r in frame.iterrows():
                t=int(idx.to_pydatetime().astimezone(timezone.utc).timestamp())
                op,hi,lo,cl=(float(r[c]) for c in ('Open','High','Low','Close'))
                if not all(__import__('math').isfinite(v) for v in (op,hi,lo,cl)):continue
                if not lo<=min(op,cl)<=max(op,cl)<=hi:continue
                # Drop incomplete current 5-minute bar (timestamps are bar start).
                if t+300>now:continue
                items.append({'time':t,'open':op,'high':hi,'low':lo,'close':cl,'volume':float(r['Volume']) if r['Volume']==r['Volume'] else 0})
            items.sort(key=lambda x:x['time'])
            if len(items)<75:raise RuntimeError(f'Nur {len(items)} vollständige Kerzen verfügbar')
            _CACHE.update(candles=items[-1300:],last_success=int(now),error=None)
        except Exception as ex:
            _CACHE['error']=str(ex)[:180]
        return dict(_CACHE)
