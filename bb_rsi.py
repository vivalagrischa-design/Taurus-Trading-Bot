"""Causal multi-timeframe Bollinger/RSI reversal research; completed 1m bars only."""
from math import sqrt
from strategies import rsi, signal_with_params, tile

def aggregate(bars, minutes):
    span=minutes*60; groups={}
    for b in bars:
        key=b['time']//span*span
        g=groups.setdefault(key,[]);g.append(b)
    result=[]
    for key,rows in sorted(groups.items()):
        if len(rows)!=minutes or rows[0]['time']!=key or rows[-1]['time']!=key+span-60:continue
        if any(rows[k+1]['time']-rows[k]['time']!=60 for k in range(len(rows)-1)):continue
        result.append(dict(time=key,open=rows[0]['open'],high=max(x['high'] for x in rows),low=min(x['low'] for x in rows),close=rows[-1]['close'],volume=sum(x.get('volume',0) for x in rows)))
    return result

def build(bars):
    names=[('bb_rsi_short','BB + RSI Extrem SHORT','SHORT'),('bb_rsi_long','BB + RSI Extrem LONG','LONG')]
    if not bars or len(bars)<75:
        return [tile(id,name,'neutral','Benötigt vollständige 1M-Daten (RSI 1M/5M/15M).',[],[('1M-Daten','red')]) for id,name,_ in names]
    series={n:aggregate(bars,n) if n>1 else bars for n in (1,5,15,60)}
    indexed={n:{b['time']+n*60:b for b in series[n]} for n in series}
    rs={n:rsi([b['close'] for b in series[n]]) for n in series}
    rmap={n:{b['time']+n*60:v for b,v in zip(series[n],rs[n]) if v is not None} for n in series}
    out={s:[] for _,_,s in names}; previous={s:False for s in out}
    last_checks={s:[] for s in out}
    for i in range(60,len(bars)):
        b=bars[i]; now=b['time']+60
        available={n:max((t for t in rmap[n] if t<=now),default=None) for n in (1,5,15,60)}
        vals={n:rmap[n].get(available[n]) for n in available}
        window=[x['close'] for x in bars[i-19:i+1]]
        mean=sum(window)/20;sd=sqrt(sum((v-mean)**2 for v in window)/20)
        upper=mean+2*sd;lower=mean-2*sd
        # 1H direction measured on the last two *completed* 1H candles.
        hs=[x for x in series[60] if x['time']+3600<=now]
        hourly_direction=0 if len(hs)<2 else (1 if hs[-1]['close']>hs[-2]['close'] else -1 if hs[-1]['close']<hs[-2]['close'] else 0)
        for side in out:
            short=side=='SHORT'; threshold=85 if short else 15
            extreme=all(vals[n] is not None and (vals[n]>threshold if short else vals[n]<threshold) for n in (1,5,15))
            band=b['close']>=upper if short else b['close']<=lower
            condition=extreme and band
            # Trigger on a new extreme episode, rearm after reset.
            if condition and not previous[side]:
                entry=b['close']; stop=(max(x['high'] for x in bars[max(0,i-4):i+1]) if short else min(x['low'] for x in bars[max(0,i-4):i+1]))
                stop= max(stop,entry*1.001) if short else min(stop,entry*.999)
                tp=entry*(.99 if short else 1.01)
                reason=f'RSI 1/5/15M extrem; BB(20,2) durchbrochen; 1H-Richtung {hourly_direction:+d}; 1H-RSI {vals[60] if vals[60] is not None else "n/v"}'
                sig=signal_with_params('bb_rsi_short' if short else 'bb_rsi_long',side,b['time'],entry,stop,tp,reason,upper if short else lower,timeframe='1m')
                sig['hourly_trend_aligned']=hourly_direction==(1 if short else -1)
                sig['hourly_rsi_extreme']=vals[60] is not None and (vals[60]>70 if short else vals[60]<30)
                out[side].append(sig)
            previous[side]=condition
            last_checks[side]=[(f'RSI 1M {vals[1]:.1f}' if vals[1] is not None else 'RSI 1M n/v','green' if extreme else 'neutral'),('RSI 5M/15M extrem','green' if extreme else 'neutral'),('BB20 ±2σ überschritten','green' if band else 'neutral'),('1H-Trend gleichgerichtet (nur Analyse)','green' if hourly_direction==(1 if short else -1) else 'neutral')]
    return [tile(id,name,'green' if out[side] and out[side][-1]['time']==bars[-1]['time'] else 'neutral','RSI 1/5/15M >85 bzw. <15 · BB(20,2) · 1H als Auswertungsmerkmal · 1% TP',out[side],last_checks[side]) for id,name,side in names]
