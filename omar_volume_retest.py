"""Omar Volume Retest v2: a separate 5M research signal for TAURUS LAB + Lucid.

Confirmed 1H HH/HL (two pivot highs + two rising pivot lows), a resistance
level known BEFORE the breakout, 5M breakout volume >= 1.5x preceding 20
completed bars, followed by a later 5M retest. Long only by default.
No broker orders. Signals are consumed by next-5M-open paper engines.
"""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from collections import defaultdict
from strategies import signal_with_params,tile

NY=ZoneInfo('America/New_York')
NAME='omar_volume_retest'
TICK={'nq':0.25,'mes':0.25,'mgc':0.10}

def hourly_complete(bars):
    """Never use an incomplete 1H candle, including at the live edge."""
    grouped=defaultdict(list)
    for b in bars:grouped[(int(b['time'])//3600)*3600].append(b)
    out=[]
    for h in sorted(grouped):
        x=sorted(grouped[h],key=lambda z:z['time'])
        if len(x)!=12 or [int(b['time']) for b in x]!=list(range(h,h+3600,300)):
            continue
        out.append(dict(time=h,high=max(float(b['high']) for b in x),
                        low=min(float(b['low']) for b in x),
                        close=float(x[-1]['close'])))
    return out

def _trend_up(hourly,at):
    """1H pivots confirmed by one completed hourly bar to the right."""
    a=[b for b in hourly if b['time']+3600<=at]
    if len(a)<7:return False
    hi=[a[i]['high'] for i in range(1,len(a)-1)
        if a[i]['high']>a[i-1]['high'] and a[i]['high']>a[i+1]['high']]
    lo=[a[i]['low'] for i in range(1,len(a)-1)
        if a[i]['low']<a[i-1]['low'] and a[i]['low']<a[i+1]['low']]
    return len(hi)>=2 and len(lo)>=2 and hi[-1]>hi[-2] and lo[-1]>lo[-2]

def _rth_levels(bars,until):
    """Latest known US cash-session open and previous completed RTH open/close.

    09:30 and 15:55 are NY local timestamps; never read future session values.
    """
    days={}
    for b in bars:
        if int(b['time'])>=until:break
        dt=datetime.fromtimestamp(int(b['time']),timezone.utc).astimezone(NY)
        if dt.weekday()>4:continue
        key=dt.date().isoformat()
        d=days.setdefault(key,{})
        if (dt.hour,dt.minute)==(9,30):d['open']=float(b['open'])
        if (dt.hour,dt.minute)==(15,55):d['close']=float(b['close'])
    if not days:return []
    keys=sorted(days)
    completed=[k for k in keys if 'open' in days[k] and 'close' in days[k]]
    levels=[]
    if completed:
        prior=days[completed[-1]]
        levels.extend([prior['open'],prior['close']])
    latest=days[keys[-1]]
    if 'open' in latest:levels.append(latest['open'])
    return levels

def _swing_levels(bars,until):
    """5M swing highs confirmed by two RIGHT-hand completed candles."""
    start=max(2,until-100)
    out=[]
    for k in range(start,until-2):
        hi=float(bars[k]['high'])
        if all(hi>float(bars[m]['high']) for m in (k-2,k-1,k+1,k+2)):
            out.append(hi)
    return out[-12:]

def _breakout(bars,j,hourly):
    if j<103 or not _trend_up(hourly,int(bars[j]['time'])+300):return []
    b=bars[j]; prev=bars[j-1]
    v=[float(x.get('volume') or 0) for x in bars[j-20:j]]
    if any(x<=0 for x in v) or float(b.get('volume') or 0)<1.5*(sum(v)/20):
        return []
    candidates=_swing_levels(bars,j)+_rth_levels(bars,int(b['time']))
    # Known levels only: previous close was at/below the resistance.
    return [lvl for lvl in candidates if float(prev['close'])<=lvl<float(b['close'])]

def _signal(bars,i,hourly,market):
    if i<105 or not _trend_up(hourly,int(bars[i]['time'])+300):return None
    b=bars[i];tick=TICK[market]
    for j in range(i-1,max(102,i-13),-1):
        levels=_breakout(bars,j,hourly)
        if not levels:continue
        for lvl in sorted(levels,key=lambda x:abs(x-float(b['close']))):
            # Confirm the FIRST valid return to the breakout level.
            tol=max(tick,0.15*sum(float(x['high'])-float(x['low']) for x in bars[max(0,i-13):i])/min(i,13))
            if not (float(b['low'])<=lvl+tol and float(b['close'])>lvl and float(b['close'])>float(b['open'])):
                continue
            already=any(float(x['low'])<=lvl+tol and float(x['close'])>lvl
                        and float(x['close'])>float(x['open']) for x in bars[j+1:i])
            if already:continue
            entry=float(b['close'])
            stop=min(float(b['low']),float(bars[j]['low']))-tick
            if stop>=entry:continue
            tp=entry+2*(entry-stop)
            return signal_with_params(NAME,'LONG',b['time'],entry,stop,tp,
                '1H HH/HL + bestätigtes 5M-Level + Breakout Volumen >= 1.5x 20 + erster Retest; next-bar OPEN, SL, 2R',
                lvl,breakout_time=bars[j]['time'],timeframe='5m')
    return None

def build(bars,market='nq'):
    if market not in TICK or len(bars)<110:
        return tile(NAME,'Omar v2 · Level + Volumen','neutral',
                    'Wartet auf vollständige 1H-Trend- und 5M-Volumendaten',[],[])
    hours=hourly_complete(bars)
    signals=[]
    # Only last 160 candles for the UI; paper engine only needs last bar.
    for i in range(max(105,len(bars)-160),len(bars)):
        sig=_signal(bars,i,hours,market)
        if sig:signals.append(sig)
    active=bool(signals and signals[-1]['time']==bars[-1]['time'])
    return tile(NAME,'Omar v2 · 1H + Volumen-Retest',
                'green' if active else 'neutral',
                'Long only · 1H HH/HL + Trendlinie · Session-/Vortageslevel oder 5M Swing · 1,5× Volumen · erster Retest · nächste 5M-Kerze · SL unter Level · 2R',
                signals,[('1H Trend HH/HL','green' if _trend_up(hours,int(bars[-1]['time'])+300) else 'neutral'),
                         ('Bestätigter Breakout & Retest','green' if active else 'neutral')])
