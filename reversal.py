"""Causal 5-minute reversal research. Each pattern is an independent paper strategy."""
from math import sqrt
from strategies import tile, signal_with_params

PATTERNS=(('rev_exhaustion','Exhaustion'),('rev_engulfing','Engulfing'),('rev_pinbar','Pin Bar'),('rev_bounce','Level Bounce'))

def build(bars):
    found={key:[] for key,_ in PATTERNS}
    if len(bars)<40:
        return [tile(key,name,'neutral','Mindestens 40 abgeschlossene 5M-Kerzen benötigt',[],[]) for key,name in PATTERNS]
    for i in range(25,len(bars)):
        b=bars[i];p=bars[i-1]; prev=bars[i-5:i]; hist=bars[i-24:i-1]
        span=max(b['high']-b['low'],b['close']*.00001)
        body=abs(b['close']-b['open']); upper=b['high']-max(b['open'],b['close']); lower=min(b['open'],b['close'])-b['low']
        avg_range=sum(x['high']-x['low'] for x in prev)/len(prev)
        up_run=p['close']>bars[i-5]['close'] and sum(x['close']>x['open'] for x in prev)>=3
        down_run=p['close']<bars[i-5]['close'] and sum(x['close']<x['open'] for x in prev)>=3
        tests=[]
        if up_run and b['close']<b['open'] and b['close']<p['close'] and max(x['high'] for x in prev)>=max(x['high'] for x in bars[i-20:i-5]):tests.append(('rev_exhaustion','SHORT','Anstieg verliert Dynamik'))
        if down_run and b['close']>b['open'] and b['close']>p['close'] and min(x['low'] for x in prev)<=min(x['low'] for x in bars[i-20:i-5]):tests.append(('rev_exhaustion','LONG','Abverkauf verliert Dynamik'))
        if b['close']>b['open'] and p['close']<p['open'] and b['open']<=p['close'] and b['close']>=p['open']:tests.append(('rev_engulfing','LONG','Bullish Engulfing'))
        if b['close']<b['open'] and p['close']>p['open'] and b['open']>=p['close'] and b['close']<=p['open']:tests.append(('rev_engulfing','SHORT','Bearish Engulfing'))
        if lower>=.55*span and upper<=.20*span and body<=.35*span:tests.append(('rev_pinbar','LONG','Unterer Docht / Zurückweisung'))
        if upper>=.55*span and lower<=.20*span and body<=.35*span:tests.append(('rev_pinbar','SHORT','Oberer Docht / Zurückweisung'))
        tolerance=max(avg_range*.45,b['close']*.00025)
        support=min(x['low'] for x in hist);resistance=max(x['high'] for x in hist)
        if abs(b['low']-support)<=tolerance and b['close']>b['open'] and b['close']>support+tolerance*.3:tests.append(('rev_bounce','LONG','Reaktion an historischer Unterstützung'))
        if abs(b['high']-resistance)<=tolerance and b['close']<b['open'] and b['close']<resistance-tolerance*.3:tests.append(('rev_bounce','SHORT','Reaktion an historischem Widerstand'))
        for key,side,reason in tests:
            # At close only; paper engine fills at next bar open.
            stop=min(x['low'] for x in bars[i-2:i+1]) if side=='LONG' else max(x['high'] for x in bars[i-2:i+1])
            entry=b['close'];stop=min(stop,entry-max(avg_range*.2,entry*.0002)) if side=='LONG' else max(stop,entry+max(avg_range*.2,entry*.0002))
            risk=abs(entry-stop);tp=entry+2*risk if side=='LONG' else entry-2*risk
            sig=signal_with_params(key,side,b['time'],entry,stop,tp,reason,stop,timeframe='5m')
            found[key].append(sig)
    return [tile(key,name,'green' if found[key] and found[key][-1]['time']==bars[-1]['time'] else 'neutral','5M-Umkehrmuster · Entry nächste Kerze · SL am Swing · TP 2R',found[key],[('Signal letzte Kerze','green' if found[key] and found[key][-1]['time']==bars[-1]['time'] else 'neutral')]) for key,name in PATTERNS]
