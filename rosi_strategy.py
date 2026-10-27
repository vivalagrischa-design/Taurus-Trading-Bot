"""Rosi PDH/PDL liquidity-sweep reversal. LAB research only.

Three independent session variants: Frankfurt, London, New York, each
08:00–10:00 local civil time (including DST). 5M completed candles only.
Previous day's high/low means last *completed* CME-style futures session
18:00–17:00 America/New_York. No current-session high/low leakage.
"""
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo

NY=ZoneInfo('America/New_York')
SESSIONS={
 'rosi_frankfurt':('Frankfurt',ZoneInfo('Europe/Berlin')),
 'rosi_london':('London',ZoneInfo('Europe/London')),
 'rosi_new_york':('New York',NY),
}
TICK={'nq':0.25,'mes':0.25,'mgc':0.10}

def _session_date(ts):
    dt=datetime.fromtimestamp(int(ts),timezone.utc).astimezone(NY)
    # CME futures session starts 18:00 NY and finishes at 17:00 NY next day.
    return (dt.date()+timedelta(days=1) if dt.hour>=18 else dt.date()).isoformat()

def _previous_levels(bars):
    """For every bar, levels from last completed futures session only.

    A session is complete after its 16:55 5M bar (ending 17:00 NY).
    If this close is absent, do not use that session as previous day.
    """
    data={}
    complete={}
    result=[]
    for b in bars:
        ts=int(b['time'])
        day=_session_date(ts)
        dt=datetime.fromtimestamp(ts,timezone.utc).astimezone(NY)
        prior=max((d for d in complete if d<day),default=None)
        result.append(complete[prior] if prior is not None else None)
        entry=data.setdefault(day,{'high':float(b['high']),'low':float(b['low'])})
        entry['high']=max(entry['high'],float(b['high']))
        entry['low']=min(entry['low'],float(b['low']))
        if dt.hour==16 and dt.minute==55:
            complete[day]=(entry['high'],entry['low'])
    return result

def _inside(ts,zone):
    dt=datetime.fromtimestamp(int(ts),timezone.utc).astimezone(zone)
    return dt.weekday()<5 and 8<=dt.hour<10

def build(bars,market='nq'):
    from strategies import tile,signal_with_params
    out=[]
    if market not in TICK or len(bars)<4:
        return [tile(key,'Rosi · '+label,'neutral',
             'Wartet auf vollständige 5M-Futuresdaten und Vortageshoch/-tief',[],[])
             for key,(label,_) in SESSIONS.items()]
    levels=_previous_levels(bars)
    tick=TICK[market]
    for key,(label,zone) in SESSIONS.items():
        signals=[]
        # Sweep bar i-1 and next-bar confirmation i; both completed.
        for i in range(2,len(bars)):
            sweep=bars[i-1];confirm=bars[i]
            if int(confirm['time'])-int(sweep['time'])!=300:continue
            if not (_inside(sweep['time'],zone) and _inside(confirm['time'],zone)):continue
            previous=levels[i-1]
            if previous is None or levels[i]!=previous:continue
            pdh,pdl=previous
            if not pdh>pdl:continue
            # PDH liquidity grab: sweep high beyond PDH, close back below,
            # bearish follow-up below both PDH and sweep close.
            short=(float(sweep['high'])>pdh and float(sweep['close'])<pdh
                and float(confirm['close'])<float(confirm['open'])
                and float(confirm['close'])<min(pdh,float(sweep['close'])))
            # PDL liquidity grab: sweep low beyond PDL, close back above,
            # bullish follow-up above both PDL and sweep close.
            long=(float(sweep['low'])<pdl and float(sweep['close'])>pdl
                and float(confirm['close'])>float(confirm['open'])
                and float(confirm['close'])>max(pdl,float(sweep['close'])))
            if not (short or long):continue
            side='SHORT' if short else 'LONG'
            entry=float(confirm['close'])
            stop=(max(float(sweep['high']),float(confirm['high']))+tick
                  if short else min(float(sweep['low']),float(confirm['low']))-tick)
            target=pdl if short else pdh
            if (short and not stop>entry>target) or (long and not stop<entry<target):
                continue
            sig=signal_with_params(key,side,confirm['time'],entry,stop,target,
                'Rosi PDH/PDL Sweep + abgeschlossene 5M-Umkehrbestätigung · '
                +label+' 08–10 lokal · nächster 5M-Open · SL hinter Sweep · TP gegenüberliegendes Vortageslevel',
                level=pdh if short else pdl,breakout_time=sweep['time'],timeframe='5m')
            signals.append(sig)
        recent=bool(signals and signals[-1]['time']==bars[-1]['time'])
        out.append(tile(key,'Rosi · '+label+' (PDH/PDL)',
          'green' if recent else 'neutral',
          '08:00–10:00 Ortszeit · Sweep PDH/PDL → Umkehrkerze → Einstieg Folgekerze · '
          'Stop hinter Sweep · Ziel gegenüberliegendes Vortageslevel · max. 200 USD Risiko (LAB)',
          signals,[('Vortageslevel vorhanden','green' if levels[-1] else 'neutral'),
                   ('Signal letzte abgeschlossene 5M-Kerze','green' if recent else 'neutral')]))
    return out
