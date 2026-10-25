"""Deterministic, look-ahead-free prototype of Omar's breakout / retest strategy.
Not a validated trading strategy. All timestamps are UTC.
"""
from datetime import datetime, timedelta, timezone
from math import sin
import random


def demo_candles(n=260):
    rng=random.Random(42)
    start=datetime(2026,10,20,12,0,tzinfo=timezone.utc)
    bars=[]
    last=24870.0
    for i in range(n):
        d=1.0 if i<155 else 0.45
        swing=11*sin(i/9)
        change=d+swing/7+rng.uniform(-6,6)
        op=last
        cl=op+change
        high=max(op,cl)+rng.uniform(2,7)
        low=min(op,cl)-rng.uniform(2,7)
        bars.append({'time':int((start+timedelta(minutes=5*i)).timestamp()),'open':round(op,2),'high':round(high,2),'low':round(low,2),'close':round(cl,2),'volume':round(rng.uniform(450,1800),0)})
        last=cl
    return bars


def pivot_high(bars, i, span=2):
    return all(bars[i]['high'] > bars[k]['high'] for k in range(i-span,i+span+1) if k!=i)


def hourly(bars):
    groups={}
    for b in bars:
        h=b['time']//3600*3600
        if h not in groups:
            groups[h]=dict(time=h,open=b['open'],high=b['high'],low=b['low'],close=b['close'],volume=b.get('volume',0))
        else:
            x=groups[h];x['high']=max(x['high'],b['high']);x['low']=min(x['low'],b['low']);x['close']=b['close'];x['volume']+=b.get('volume',0)
    # Only completed 1h candles, NEVER include the current partial hour.
    if bars:
        groups.pop(bars[-1]['time']//3600*3600,None)
    return list(groups.values())


def assess(bars, risk=200):
    if len(bars)<75:
        return {'stage':'INSUFFICIENT','reason':'Mindestens 75 abgeschlossene 5M-Kerzen benötigt','signals':[]}
    # Causal scanning: use bars strictly before candidate bar for level and hourly trend.
    events=[]; last_stage='SUCHT SETUP'; stage_time=None; last_level=None
    for i in range(65,len(bars)):
        current=bars[i]; past=bars[:i]
        hs=hourly(past)
        # Structural filter. Explicitly a prototype, not a full trendline implementation.
        if len(hs)<5: continue
        ups=hs[-1]['close']>hs[-3]['close'] and hs[-1]['low']>hs[-4]['low']
        downs=hs[-1]['close']<hs[-3]['close'] and hs[-1]['high']<hs[-4]['high']
        if not (ups or downs): continue
        side='LONG' if ups else 'SHORT'
        # A known pivot requires 2 bars of confirmation; bar i-3 latest eligible.
        eligible=range(max(2,i-54),i-2)
        pivots=[k for k in eligible if k+2<i and (pivot_high(bars,k) if ups else all(bars[k]['low'] < bars[t]['low'] for t in range(k-2,k+3) if t!=k))]
        if not pivots: continue
        k=pivots[-1]
        level=bars[k]['high'] if ups else bars[k]['low']
        tol= max(3,level*0.00018)
        # Breakout of historically known level in last 1..5 completed candles.
        breaks=[]
        for j in range(max(k+3,i-5),i):
            if j<1:continue
            if side=='LONG' and bars[j]['close']>level+tol and bars[j-1]['close']<=level+tol:breaks.append(j)
            if side=='SHORT' and bars[j]['close']<level-tol and bars[j-1]['close']>=level-tol:breaks.append(j)
        if not breaks:continue
        bidx=breaks[-1]
        if bidx>=i:continue
        # Retest touches level and candle closes on correct side.
        touch=(current['low']<=level+tol if ups else current['high']>=level-tol)
        valid=(current['close']>level if ups else current['close']<level)
        last_level=round(level,2)
        if touch and valid:
            entry=current['close']
            stop=(min(x['low'] for x in bars[max(bidx,i-2):i+1])-tol if ups else max(x['high'] for x in bars[max(bidx,i-2):i+1])+tol)
            dist=abs(entry-stop)
            if dist<1:continue
            tp=entry+(2*dist if ups else -2*dist)
            # MNQ $2/point, whole contracts, max risk <= budget, ignoring costs.
            contracts=max(0,int(risk//(dist*2)))
            ev={'id':str(current['time'])+'-'+side,'time':current['time'],'side':side,'entry':round(entry,2),'stop':round(stop,2),'tp':round(tp,2),'level':round(level,2),'risk_points':round(dist,2),'mnq_contracts':contracts,'breakout_time':bars[bidx]['time'],'status':'SIMULIERT / NICHT GEHANDELT'}
            if not events or events[-1]['time']!=current['time']: events.append(ev)
            last_stage='SIGNAL BESTÄTIGT';stage_time=current['time']
        else:
            last_stage='RETEST WIRD GEPRÜFT';stage_time=current['time']
    return {'stage':last_stage,'stage_time':stage_time,'level':last_level,'signals':events[-25:][::-1],'candles':bars[-210:],'last_bar_time':bars[-1]['time'],'risk_usd':risk}
