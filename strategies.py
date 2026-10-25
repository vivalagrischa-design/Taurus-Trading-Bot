"""Experimental multi-strategy signal summaries. Completed historical candles ONLY.
No return/win-rate claims, no execution, not a validated backtest.
"""
from datetime import datetime, timezone
from engine import assess


def ema(values, period):
    out=[]; avg=None; k=2/(period+1)
    for value in values:
        avg=value if avg is None else avg+(value-avg)*k
        out.append(avg)
    return out


def rsi(values, period=14):
    out=[None]*len(values)
    if len(values)<=period:return out
    gains=[max(values[i]-values[i-1],0) for i in range(1,len(values))]
    losses=[max(values[i-1]-values[i],0) for i in range(1,len(values))]
    g=sum(gains[:period])/period;l=sum(losses[:period])/period
    for i in range(period,len(values)):
        if i>period:g=(g*(period-1)+gains[i-1])/period;l=(l*(period-1)+losses[i-1])/period
        out[i]=100 if l==0 else 100-100/(1+g/l)
    return out


def signal(id,side,bars,i,reason,level=None):
    b=bars[i];entry=b['close'];dist=max(b['high']-b['low'],2)
    stop=entry-dist if side=='LONG' else entry+dist
    tp=entry+2*dist if side=='LONG' else entry-2*dist
    return dict(id=f'{id}-{b["time"]}',strategy=id,time=b['time'],side=side,entry=round(entry,2),stop=round(stop,2),tp=round(tp,2),level=round(level if level is not None else entry,2),breakout_time=b['time'],mnq_contracts=int(200//(dist*2)),status='HISTORISCHES TESTSIGNAL',reason=reason)


def tile(id,name,state,details,signals,checks):
    return dict(id=id,name=name,state=state,details=details,signals=signals[-25:][::-1],checks=checks)


def evaluate(bars):
    if len(bars)<75:return []
    closes=[b['close'] for b in bars]; e20=ema(closes,20); e50=ema(closes,50); rs=rsi(closes)
    result=[]
    o=assess(bars);osigs=[dict(s,strategy='omar',reason='1H-Richtung, Breakout und Retest (vereinfachter Prototyp)') for s in reversed(o.get('signals',[]))]
    current=osigs[-1] if osigs else None
    trend_up=e20[-1]>e50[-1];trend_down=e20[-1]<e50[-1]
    result.append(tile('omar','Omar Breakout / Retest','green' if current and current['time']==bars[-1]['time'] else 'yellow' if 'RETEST' in o['stage'] else 'neutral',o['stage'],osigs,[('1H-Trend','green' if trend_up or trend_down else 'neutral'),('Level gefunden','green' if o.get('level') else 'neutral'),('Retest','green' if current and current['time']==bars[-1]['time'] else 'neutral')]))
    ema_sigs=[];rsi_sigs=[]
    for i in range(51,len(bars)):
        # EMA20 confirmation only on candle close. First close crossing the EMA20 in trend direction.
        if e20[i]>e50[i] and closes[i-1]<=e20[i-1] and closes[i]>e20[i]:ema_sigs.append(signal('ema20','LONG',bars,i,'EMA20-Rückeroberung bei EMA20 > EMA50',e20[i]))
        if e20[i]<e50[i] and closes[i-1]>=e20[i-1] and closes[i]<e20[i]:ema_sigs.append(signal('ema20','SHORT',bars,i,'EMA20-Abweisung bei EMA20 < EMA50',e20[i]))
        # RSI 30/70 crossings in same direction as EMA50; deliberately exploratory.
        if rs[i] is not None and rs[i-1] is not None:
            if rs[i-1]<=30<rs[i] and closes[i]>e50[i]:rsi_sigs.append(signal('rsi_ema','LONG',bars,i,'RSI kreuzt 30 aufwärts und Kurs > EMA50'))
            if rs[i-1]>=70>rs[i] and closes[i]<e50[i]:rsi_sigs.append(signal('rsi_ema','SHORT',bars,i,'RSI kreuzt 70 abwärts und Kurs < EMA50'))
    recent=lambda s:bool(s and s[-1]['time']==bars[-1]['time'])
    result.append(tile('rsi_ema','RSI + EMA','green' if recent(rsi_sigs) else 'red' if rs[-1] is not None and (rs[-1]>=70 or rs[-1]<=30) else 'neutral',f'RSI14 {rs[-1]:.1f} · EMA50-Filter',rsi_sigs,[('RSI überverkauft (≤30)','green' if rs[-1]<=30 else 'neutral'),('RSI überkauft (≥70)','red' if rs[-1]>=70 else 'neutral'),('Signal auf letzter Kerze','green' if recent(rsi_sigs) else 'neutral')]))
    result.append(tile('ema20','EMA20','green' if recent(ema_sigs) else 'red' if closes[-1]<e20[-1] else 'neutral',f'EMA20 {e20[-1]:.2f} · EMA50 {e50[-1]:.2f}',ema_sigs,[('Kurs über EMA20','green' if closes[-1]>e20[-1] else 'red'),('EMA20 > EMA50','green' if trend_up else 'red'),('Signal auf letzter Kerze','green' if recent(ema_sigs) else 'neutral')]))
    # ORB: needs real trading session metadata, timezone and opening-range hours.
    result.append(tile('orb','ORB / Pre-Market Bias','neutral','Noch nicht aktiviert: Handelszeiten, Zeitzone und Opening-Range-Definition fehlen.',[],[('Regeln vollständig','red'),('Sitzungsdefinition','red'),('Signal verfügbar','neutral')]))
    return result
