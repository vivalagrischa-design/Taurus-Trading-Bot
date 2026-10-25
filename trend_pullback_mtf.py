"""TAURUS research-only 1H trend + 5M pullback momentum scanner.
Uses completed candles only; signals at close, paper execution at next 5M open.
"""
def _ema(values, span):
    out=[]; alpha=2/(span+1); last=None
    for value in values:
        last=value if last is None else alpha*value+(1-alpha)*last
        out.append(last)
    return out

def build(bars):
    ident='trend_pullback_mtf'
    signals=[]
    if len(bars)<110:
        return {'id':ident,'name':'Trend 1H + Pullback 5M + Momentum','state':'neutral',
                'details':'Wartet auf mindestens 110 abgeschlossene 5M-Kerzen',
                'signals':[],'checks':[('1H Trend','neutral'),('5M Pullback','neutral'),('Momentum-Bestätigung','neutral')]}
    closes=[float(b['close']) for b in bars]
    ma20=_ema(closes,20)
    for i in range(110,len(bars)):
        b=bars[i]; p=bars[i-1]
        # 1h aggregates strictly before the signal hour; exclude partial hours.
        cutoff=int(b['time'])//3600*3600
        h=[]
        for bar in bars[:i]:
            hour=int(bar['time'])//3600*3600
            if hour>=cutoff: break
            if not h or h[-1]['time']!=hour:
                h.append({'time':hour,'high':float(bar['high']),'low':float(bar['low']),'close':float(bar['close'])})
            else:
                h[-1]['high']=max(h[-1]['high'],float(bar['high']))
                h[-1]['low']=min(h[-1]['low'],float(bar['low']))
                h[-1]['close']=float(bar['close'])
        if len(h)<50: continue
        ema50=_ema([x['close'] for x in h],50)
        up=(ema50[-1]>ema50[-4] and h[-1]['high']>h[-3]['high'] and h[-1]['low']>h[-3]['low'])
        down=(ema50[-1]<ema50[-4] and h[-1]['high']<h[-3]['high'] and h[-1]['low']<h[-3]['low'])
        if not (up or down):continue
        # Intraday VWAP (UTC calendar-day reset); crypto volume and Yahoo volume proxies.
        day=int(b['time'])//86400
        window=[x for x in bars[max(0,i-287):i+1] if int(x['time'])//86400==day]
        v=sum(max(0.,float(x.get('volume',0) or 0)) for x in window)
        vwap=(sum(((float(x['high'])+float(x['low'])+float(x['close']))/3)*max(0.,float(x.get('volume',0) or 0)) for x in window)/v) if v else None
        prev=float(p['close']); price=float(b['close'])
        # Previous confirmed bar touched / crossed EMA20 or VWAP; no future bar references.
        near_ema=(float(p['low'])<=ma20[i-1] if up else float(p['high'])>=ma20[i-1])
        near_vwap=(vwap is not None and (float(p['low'])<=vwap if up else float(p['high'])>=vwap))
        if not (near_ema or near_vwap): continue
        is_long=up and price>float(p['high']) and price>ma20[i] and price>float(b['open'])
        is_short=down and price<float(p['low']) and price<ma20[i] and price<float(b['open'])
        if not (is_long or is_short):continue
        side='LONG' if is_long else 'SHORT'
        recent=bars[max(0,i-4):i+1]
        stop=min(float(x['low']) for x in recent) if is_long else max(float(x['high']) for x in recent)
        dist=price-stop if is_long else stop-price
        if dist<=0:continue
        tp=price+(2*dist if is_long else -2*dist)
        signals.append({'id':f'{ident}-{b["time"]}','strategy':ident,'time':int(b['time']),
            'side':side,'entry':round(price,6),'stop':round(stop,6),'tp':round(tp,6),
            'level':round(ma20[i],6),'breakout_time':int(b['time']),
            'mnq_contracts':None,'status':'HISTORISCHES TESTSIGNAL',
            'reason':'Abgeschlossener 1H-Trend, 5M Pullback an EMA20/VWAP, Kerzenschluss über/unter vorheriger Kerze',
            'timeframe':'5m'})
    recent=bool(signals and signals[-1]['time']==bars[-1]['time'])
    return {'id':ident,'name':'Trend 1H + Pullback 5M + Momentum','state':'green' if recent else 'neutral',
       'details':'1H EMA50 + höhere Hochs/Tiefs; 5M EMA20/VWAP; Momentum; 2R Testziel, Paper-Entry nächste 5M-Kerze',
       'signals':signals[::-1],
       'checks':[('1H Trend und EMA50','green' if recent else 'neutral'),
                 ('5M EMA20/VWAP Pullback','green' if recent else 'neutral'),
                 ('Momentum bestätigt','green' if recent else 'neutral')]}
