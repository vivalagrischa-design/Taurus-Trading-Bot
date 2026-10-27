"""Experimental TAURUS multi-strategy signal summaries.
Completed candles only. Research mode, no execution advice.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from engine import assess

NY = ZoneInfo('America/New_York')


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


def signal(id,side,bars,i,reason,level=None,timeframe='5m',rr=2.0):
    b=bars[i]
    entry=b['close']
    dist=max(abs(b['high']-b['low']), max(entry*0.0012, 1.0 if entry>100 else 0.01))
    stop=entry-dist if side=='LONG' else entry+dist
    tp=entry+rr*dist if side=='LONG' else entry-rr*dist
    return dict(
        id=f'{id}-{b["time"]}', strategy=id, time=b['time'], side=side,
        entry=round(entry,4), stop=round(stop,4), tp=round(tp,4), level=round(level if level is not None else entry,4),
        breakout_time=b['time'], mnq_contracts=max(0,int(200//max(1,dist*2))) if entry>100 else None,
        status='HISTORISCHES TESTSIGNAL', reason=reason, timeframe=timeframe
    )


def signal_with_params(id,side,time,entry,stop,tp,reason,level=None,breakout_time=None,timeframe='1m'):
    dist=abs(entry-stop)
    return dict(
        id=f'{id}-{time}', strategy=id, time=int(time), side=side,
        entry=round(entry,4), stop=round(stop,4), tp=round(tp,4), level=round(level if level is not None else entry,4),
        breakout_time=int(breakout_time or time), mnq_contracts=max(0,int(200//max(1,dist*2))) if entry>100 else None,
        status='HISTORISCHES TESTSIGNAL', reason=reason, timeframe=timeframe
    )


def tile(id,name,state,details,signals,checks):
    return dict(id=id,name=name,state=state,details=details,signals=signals[::-1],checks=checks)


def _ny_dt(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).astimezone(NY)


def _by_session(bars):
    sessions={}
    for i,b in enumerate(bars):
        dt=_ny_dt(b['time'])
        key=dt.date().isoformat()
        sessions.setdefault(key,[]).append((i,dt,b))
    return sessions


def _orb_signals_5m(bars, enabled=True):
    if not enabled:
        return tile('orb','ORB / Opening Range Breakout','neutral','Nur für Nasdaq / US-Open aktivierbar.',[],[('US-Session erkannt','neutral'),('Opening Range 09:30–10:00 NY','neutral'),('Breakout / Retest','neutral')])
    signals=[]; direct_today=False; retest_today=False; todays_detail='Wartet auf 09:30 NY'
    sessions=_by_session(bars)
    last_date=max(sessions) if sessions else None
    for key,rows in sessions.items():
        sess=[(i,dt,b) for i,dt,b in rows if (dt.hour>9 or (dt.hour==9 and dt.minute>=30)) and (dt.hour<16)]
        if len(sess)<8: 
            continue
        opening=[item for item in sess if item[1].hour==9 and 30<=item[1].minute<60] + [item for item in sess if item[1].hour==10 and item[1].minute==0]
        opening=opening[:6]
        if len(opening)<6:
            if key==last_date: todays_detail='Opening Range unvollständig'
            continue
        r_high=max(b['high'] for _,_,b in opening)
        r_low=min(b['low'] for _,_,b in opening)
        after=sess[6:]
        long_break=None; short_break=None
        prev_close=opening[-1][2]['close']
        for i,dt,b in after:
            if long_break is None and b['close']>r_high and prev_close<=r_high:
                stop=max(r_low, b['close']-(b['close']-r_low)*0.55)
                tp=b['close'] + 1.6*(b['close']-stop)
                signals.append(signal_with_params('orb','LONG',b['time'],b['close'],stop,tp,'ORB Direkt-Breakout über die Opening Range',level=r_high,breakout_time=b['time'],timeframe='5m'))
                long_break=b
                if key==last_date: direct_today=True; todays_detail='Direkt-Breakout über OR hoch'
            if short_break is None and b['close']<r_low and prev_close>=r_low:
                stop=min(r_high, b['close']+(r_high-b['close'])*0.55)
                tp=b['close'] - 1.6*(stop-b['close'])
                signals.append(signal_with_params('orb','SHORT',b['time'],b['close'],stop,tp,'ORB Direkt-Breakout unter die Opening Range',level=r_low,breakout_time=b['time'],timeframe='5m'))
                short_break=b
                if key==last_date: direct_today=True; todays_detail='Direkt-Breakout unter OR tief'
            if long_break and not retest_today and b['low']<=r_high and b['close']>r_high and b['time']>long_break['time']:
                stop=min(x['low'] for _,_,x in sess[max(0, sess.index((i,dt,b))-3):sess.index((i,dt,b))+1])
                dist=max(b['close']-stop, max(b['close']*0.0008, 1.0))
                signals.append(signal_with_params('orb','LONG',b['time'],b['close'],b['close']-dist,b['close']+1.8*dist,'ORB Retest des Opening-Range-Ausbruchs',level=r_high,breakout_time=long_break['time'],timeframe='5m'))
                if key==last_date: retest_today=True; todays_detail='Retest Long bestätigt'
            if short_break and not retest_today and b['high']>=r_low and b['close']<r_low and b['time']>short_break['time']:
                stop=max(x['high'] for _,_,x in sess[max(0, sess.index((i,dt,b))-3):sess.index((i,dt,b))+1])
                dist=max(stop-b['close'], max(b['close']*0.0008, 1.0))
                signals.append(signal_with_params('orb','SHORT',b['time'],b['close'],b['close']+dist,b['close']-1.8*dist,'ORB Retest des Opening-Range-Ausbruchs',level=r_low,breakout_time=short_break['time'],timeframe='5m'))
                if key==last_date: retest_today=True; todays_detail='Retest Short bestätigt'
            prev_close=b['close']
    recent=bool(signals and signals[-1]['time']==bars[-1]['time'])
    state='green' if recent else 'yellow' if (direct_today or retest_today) else 'neutral'
    checks=[('US-Session erkannt','green'),('Opening Range 09:30–10:00 NY','green'),('Breakout / Retest','green' if (direct_today or retest_today) else 'neutral')]
    return tile('orb','ORB / Opening Range Breakout',state,todays_detail,signals,checks)


def _opening_signals_1m(bars1m, enabled=True):
    if not enabled or len(bars1m)<120:
        neutral=tile('opening_drop','Opening Drop Short','neutral','Nur für Nasdaq / US-Open mit 1-Minuten-Daten.',[],[('Markt geöffnet','neutral'),('Früher Drop läuft','neutral'),('Short-Signal','neutral')])
        rev=tile('opening_reversal','Opening Reversal Long','neutral','Nur für Nasdaq / US-Open mit 1-Minuten-Daten.',[],[('Drop ≥ 0.25 %','neutral'),('Talsohle stabilisiert','neutral'),('Long-Reversal','neutral')])
        return neutral, rev
    short_signals=[]; long_signals=[]
    today_short='Wartet auf Drop'; today_long='Wartet auf Reversal'
    short_ready=False; long_ready=False; drawdown_today=0
    for key,rows in _by_session(bars1m).items():
        sess=[(i,dt,b) for i,dt,b in rows if (dt.hour>9 or (dt.hour==9 and dt.minute>=30)) and (dt.hour<11 or (dt.hour==11 and dt.minute==0))]
        if len(sess)<25:
            continue
        open_price=sess[0][2]['open']
        cumulative_pv=0.0; cumulative_v=0.0
        lows=[]; closes=[]
        day_short=False; day_long=False
        session_low=open_price
        max_drop=0.0
        for pos,(i,dt,b) in enumerate(sess):
            vol=max(float(b.get('volume',0) or 0),1.0)
            typical=(b['high']+b['low']+b['close'])/3
            cumulative_pv+=typical*vol; cumulative_v+=vol
            vwap=cumulative_pv/cumulative_v if cumulative_v else b['close']
            closes.append(b['close']); lows.append(b['low'])
            session_low=min(session_low,b['low'])
            max_drop=max(max_drop,(open_price-session_low)/open_price)
            # Short: after 09:35, price below open and VWAP with fresh downside push.
            if pos>=5 and not day_short:
                last5=sess[max(0,pos-4):pos+1]
                recent_high=max(x[2]['high'] for x in last5)
                recent_low=min(x[2]['low'] for x in last5)
                below_open=(open_price-b['close'])/open_price>=0.0015
                momentum_down=b['close']<closes[-2] and b['low']<=recent_low
                if below_open and b['close']<vwap and momentum_down and dt.hour<10:
                    stop=max(recent_high, b['close']*1.001)
                    dist=max(stop-b['close'], max(b['close']*0.0008, 1.0))
                    short_signals.append(signal_with_params('opening_drop','SHORT',b['time'],b['close'],b['close']+dist,b['close']-1.4*dist,'Opening Drop Short (1M Entry innerhalb der frühen Abwärtsbewegung)',level=open_price,breakout_time=sess[0][2]['time'],timeframe='1m'))
                    day_short=True
            # Long reversal: require prior drawdown, then higher low + breakout above recent highs + back above VWAP.
            if pos>=12 and not day_long and max_drop>=0.0025:
                recent=sess[max(0,pos-6):pos+1]
                recent_high=max(x[2]['high'] for x in recent[:-1])
                prev_lows=[x[2]['low'] for x in sess[max(0,pos-4):pos]]
                higher_low=b['low']>min(prev_lows) if prev_lows else False
                breakout_up=b['close']>recent_high
                if breakout_up and higher_low and b['close']>vwap:
                    stop=min(x[2]['low'] for x in recent)
                    dist=max(b['close']-stop, max(b['close']*0.0008, 1.0))
                    long_signals.append(signal_with_params('opening_reversal','LONG',b['time'],b['close'],b['close']-dist,b['close']+1.4*dist,'Opening Reversal Long nach bestätigter Talsohle',level=session_low,breakout_time=b['time'],timeframe='1m'))
                    day_long=True
        # today's status
        last_session=max(_by_session(bars1m)) if bars1m else None
        if key==last_session:
            drawdown_today=max_drop
            short_ready=day_short
            long_ready=day_long
            today_short='Short-Signal aktiv' if day_short else ('Drop läuft, aber noch kein Short-Trigger' if max_drop>=0.001 else 'Wartet auf Opening Drop')
            today_long='Long-Reversal bestätigt' if day_long else ('Drop gesehen, wartet auf Umkehr' if max_drop>=0.0025 else 'Noch kein ausreichender Drop')
    short_tile=tile('opening_drop','Opening Drop Short','green' if short_ready else 'yellow' if drawdown_today>=0.001 else 'neutral',today_short,short_signals,[('Markt geöffnet','green'),('Früher Drop läuft','green' if drawdown_today>=0.001 else 'neutral'),('Short-Signal','green' if short_ready else 'neutral')])
    long_tile=tile('opening_reversal','Opening Reversal Long','green' if long_ready else 'yellow' if drawdown_today>=0.0025 else 'neutral',today_long,long_signals,[('Drop ≥ 0.25 %','green' if drawdown_today>=0.0025 else 'neutral'),('Talsohle stabilisiert','green' if long_ready else 'neutral'),('Long-Reversal','green' if long_ready else 'neutral')])
    return short_tile, long_tile



def _simple_repetitive(bars, market):
    """Two simple 5m research signals; strictly closed bars and no lookahead."""
    names=[('trend_pullback','Trend EMA20 Pullback'),('bb_rsi_scale','BB+RSI gestaffelt (max. 3)')]
    found={name:[] for name,_ in names}
    if len(bars)<80:
        return [tile(name,label,'neutral','Mindestens 80 abgeschlossene 5M-Kerzen',[],[]) for name,label in names]
    closes=[float(b['close']) for b in bars]
    ma20=ema(closes,20);ma50=ema(closes,50);rs=rsi(closes)
    from math import sqrt
    for i in range(60,len(bars)):
        b=bars[i];p=bars[i-1];price=float(b['close'])
        window=closes[i-19:i+1];mid=sum(window)/20
        sd=sqrt(sum((x-mid)**2 for x in window)/20)
        upper=mid+2*sd;lower=mid-2*sd
        if sd==0:continue
        # Moving averages aligned and rising/falling over five completed 5m bars.
        up=ma20[i]>ma50[i] and ma20[i]>ma20[i-5] and ma50[i]>ma50[i-5]
        down=ma20[i]<ma50[i] and ma20[i]<ma20[i-5] and ma50[i]<ma50[i-5]
        if up and p['close']<=ma20[i-1] and price>ma20[i] and price>p['high']:
            stop=min(x['low'] for x in bars[i-3:i+1])
            if stop<price:found['trend_pullback'].append(signal_with_params('trend_pullback','LONG',b['time'],price,stop,price+2*(price-stop),'EMA20 pullback in rising EMA20/EMA50 trend',ma20[i],timeframe='5m'))
        if down and p['close']>=ma20[i-1] and price<ma20[i] and price<p['low']:
            stop=max(x['high'] for x in bars[i-3:i+1])
            if stop>price:found['trend_pullback'].append(signal_with_params('trend_pullback','SHORT',b['time'],price,stop,price-2*(stop-price),'EMA20 pullback in falling EMA20/EMA50 trend',ma20[i],timeframe='5m'))
        # Countertrend mean reversion: avoid strong monotonic EMA trend; separate
        # this experiment from the strict 1M/5M/15M extreme variants.
        extreme_short=rs[i] is not None and rs[i]>=80 and price>=upper
        extreme_long=rs[i] is not None and rs[i]<=20 and price<=lower
        if extreme_short or extreme_long:
            side='SHORT' if extreme_short else 'LONG'
            stop=price*(1.015 if side=='SHORT' else .985)
            tp=price*(.995 if side=='SHORT' else 1.005)
            found['bb_rsi_scale'].append(signal_with_params('bb_rsi_scale',side,b['time'],price,stop,tp,'5M BB20 outer band + RSI extreme; capped three-leg net-TP cycle',upper if extreme_short else lower,timeframe='5m'))
    return [tile(name,label,'green' if found[name] and found[name][-1]['time']==bars[-1]['time'] else 'neutral','5M Entry nächste Kerze; max. 200 USD Gesamtrisiko; BB+RSI: gestaffelt und gemeinsames Nettoziel',found[name],[('Signal letzte Kerze','green' if found[name] and found[name][-1]['time']==bars[-1]['time'] else 'neutral')]) for name,label in names]


def evaluate(bars, bars1m=None, market='nq'):
    if len(bars)<75:return []
    closes=[b['close'] for b in bars]; e20=ema(closes,20); e50=ema(closes,50); rs=rsi(closes)
    result=[]
    o=assess(bars)
    osigs=[dict(s,strategy='omar',reason='1H-Richtung, Breakout und Retest (vereinfachter Prototyp)',timeframe='5m') for s in reversed(o.get('signals',[]))]
    current=osigs[-1] if osigs else None
    trend_up=e20[-1]>e50[-1];trend_down=e20[-1]<e50[-1]
    result.append(tile('omar','Omar Breakout / Retest','green' if current and current['time']==bars[-1]['time'] else 'yellow' if 'RETEST' in o['stage'] else 'neutral',o['stage'],osigs,[('1H-Trend','green' if trend_up or trend_down else 'neutral'),('Level gefunden','green' if o.get('level') else 'neutral'),('Retest','green' if current and current['time']==bars[-1]['time'] else 'neutral')]))
    from omar_volume_retest import build as omar_v2_build
    result.append(omar_v2_build(bars,market))
    ema_sigs=[];rsi_sigs=[]
    for i in range(51,len(bars)):
        if e20[i]>e50[i] and closes[i-1]<=e20[i-1] and closes[i]>e20[i]:ema_sigs.append(signal('ema20','LONG',bars,i,'EMA20-Rückeroberung bei EMA20 > EMA50',e20[i]))
        if e20[i]<e50[i] and closes[i-1]>=e20[i-1] and closes[i]<e20[i]:ema_sigs.append(signal('ema20','SHORT',bars,i,'EMA20-Abweisung bei EMA20 < EMA50',e20[i]))
        if rs[i] is not None and rs[i-1] is not None:
            if rs[i-1]<=30<rs[i] and closes[i]>e50[i]:rsi_sigs.append(signal('rsi_ema','LONG',bars,i,'RSI kreuzt 30 aufwärts und Kurs > EMA50'))
            if rs[i-1]>=70>rs[i] and closes[i]<e50[i]:rsi_sigs.append(signal('rsi_ema','SHORT',bars,i,'RSI kreuzt 70 abwärts und Kurs < EMA50'))
    recent=lambda s:bool(s and s[-1]['time']==bars[-1]['time'])
    result.append(tile('rsi_ema','RSI + EMA','green' if recent(rsi_sigs) else 'red' if rs[-1] is not None and (rs[-1]>=70 or rs[-1]<=30) else 'neutral',f'RSI14 {rs[-1]:.1f} · EMA50-Filter',rsi_sigs,[('RSI überverkauft (≤30)','green' if rs[-1] and rs[-1]<=30 else 'neutral'),('RSI überkauft (≥70)','red' if rs[-1] and rs[-1]>=70 else 'neutral'),('Signal auf letzter Kerze','green' if recent(rsi_sigs) else 'neutral')]))
    result.append(tile('ema20','EMA20','green' if recent(ema_sigs) else 'red' if closes[-1]<e20[-1] else 'neutral',f'EMA20 {e20[-1]:.2f} · EMA50 {e50[-1]:.2f}',ema_sigs,[('Kurs über EMA20','green' if closes[-1]>e20[-1] else 'red'),('EMA20 > EMA50','green' if trend_up else 'red'),('Signal auf letzter Kerze','green' if recent(ema_sigs) else 'neutral')]))
    result.append(_orb_signals_5m(bars, enabled=(market=='nq')))
    short_tile,long_tile=_opening_signals_1m(bars1m or [], enabled=(market=='nq'))
    result.extend([short_tile,long_tile])
    from bb_rsi import build
    result.extend(build(bars1m or []))
    from reversal import build as reversal_build
    result.extend(reversal_build(bars))
    result.extend(_simple_repetitive(bars,market))
    from trend_pullback_mtf import build as trend_mtf_build
    result.append(trend_mtf_build(bars))
    return result
