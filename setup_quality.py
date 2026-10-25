"""Causal diagnostic setup score, NOT a probability or trading recommendation."""
import math

def score_signal(signal,history):
    if not history: return {'score':0,'components':{},'grade':'UNAVAILABLE'}
    closes=[float(b['close']) for b in history]
    if len(closes)<50:return {'score':0,'components':{},'grade':'INSUFFICIENT'}
    price=closes[-1];side=signal.get('side','')
    if side not in ('LONG','SHORT'):return {'score':0,'components':{},'grade':'UNKNOWN'}
    direction=1 if side=='LONG' else -1
    ema20=sum(closes[-20:])/20
    ema50=sum(closes[-50:])/50
    trend=25 if (ema20-ema50)*direction>0 else 0
    vals=closes[-20:];mean=sum(vals)/len(vals)
    sd=math.sqrt(sum((c-mean)**2 for c in vals)/len(vals))
    band=(price-(mean-2*sd))/(4*sd) if sd else 0.5
    bb=25 if (band<=.10 and direction==1) or (band>=.90 and direction==-1) else 10 if .2<=band<=.8 else 0
    volume=[float(b.get('volume') or 0) for b in history[-21:]]
    avg=sum(volume[:-1])/max(1,len(volume)-1)
    vol=20 if avg>0 and volume[-1]>=1.5*avg else 10 if avg>0 and volume[-1]>=avg else 0
    level=signal.get('level')
    proximity=0
    if isinstance(level,(int,float)) and price:
        proximity=30 if abs(price-level)/abs(price)<0.001 else 15 if abs(price-level)/abs(price)<0.003 else 0
    components={'trend':trend,'bb_context':bb,'volume':vol,'level_proximity':proximity}
    value=sum(components.values())
    return {'score':value,'components':components,'grade':'A' if value>=75 else 'B' if value>=55 else 'C'}
