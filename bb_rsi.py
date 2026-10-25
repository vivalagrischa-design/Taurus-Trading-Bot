"""Three independent, causal BB reversal variants; only completed 1m candles."""
from math import sqrt
from strategies import rsi,signal_with_params,tile

VARIANTS=[('bb_only_short','A · BB SHORT','SHORT','A'),('bb_only_long','A · BB LONG','LONG','A'),
 ('bb_rsi_short','B · BB + RSI SHORT','SHORT','B'),('bb_rsi_long','B · BB + RSI LONG','LONG','B'),
 ('bb_reversal_short','C · BB + Umkehr SHORT','SHORT','C'),('bb_reversal_long','C · BB + Umkehr LONG','LONG','C')]

def aggregate(bars,minutes):
    groups={};period=minutes*60
    for b in bars:groups.setdefault(b['time']//period*period,[]).append(b)
    result=[]
    for start,rows in sorted(groups.items()):
        if len(rows)!=minutes or rows[0]['time']!=start or rows[-1]['time']!=start+period-60:continue
        if any(rows[j+1]['time']-rows[j]['time']!=60 for j in range(len(rows)-1)):continue
        result.append(dict(time=start,open=rows[0]['open'],high=max(x['high'] for x in rows),
          low=min(x['low'] for x in rows),close=rows[-1]['close'],volume=sum(x.get('volume',0) for x in rows)))
    return result

def build(bars):
    results={name:[] for name,_,_,_ in VARIANTS}
    checks={name:[] for name in results}
    if not bars or len(bars)<320:
        return [tile(name,label,'neutral','Benötigt mindestens 320 vollständige 1M-Kerzen für BB20 auf 15M.',[],[('Daten ausreichend','red')]) for name,label,_,_ in VARIANTS]
    series={n:aggregate(bars,n) if n>1 else bars for n in (1,5,15)}
    bands={};rsi_maps={}
    for n,seq in series.items():
        vals={};readings=rsi([b['close'] for b in seq])
        rsi_maps[n]={b['time']+n*60:v for b,v in zip(seq,readings) if v is not None}
        for j in range(19,len(seq)):
            window=[float(x['close']) for x in seq[j-19:j+1]]
            avg=sum(window)/20;sd=sqrt(sum((x-avg)**2 for x in window)/20)
            vals[seq[j]['time']+n*60]=(float(seq[j]['close']),avg+2*sd,avg-2*sd)
        bands[n]=vals
    # Retest after the extreme: keep C armed for up to five subsequent 1M closes.
    armed={'LONG':None,'SHORT':None}
    previous={(kind,side):False for kind in ('A','B') for side in ('LONG','SHORT')}
    for i in range(300,len(bars)):
        now=bars[i]['time']+60;b=bars[i]
        obs={};rvals={}
        for n in (1,5,15):
            valid=[t for t in bands[n] if t<=now]
            obs[n]=bands[n][max(valid)] if valid else None
            rt=[t for t in rsi_maps[n] if t<=now]
            rvals[n]=rsi_maps[n][max(rt)] if rt else None
        for side in ('SHORT','LONG'):
            short=side=='SHORT'
            bb=all(obs[n] is not None and (obs[n][0]>obs[n][1] if short else obs[n][0]<obs[n][2]) for n in (1,5,15))
            extreme=all(rvals[n] is not None and (rvals[n]>85 if short else rvals[n]<15) for n in (1,5,15))
            for kind in ('A','B'):
                condition=bb and (kind=='A' or extreme)
                name=('bb_only_' if kind=='A' else 'bb_rsi_')+side.lower()
                if condition and not previous[(kind,side)]:
                    _add(results[name],name,side,bars,i,obs[1],kind+' BB1/5/15'+(' RSI1/5/15' if kind=='B' else ''))
                previous[(kind,side)]=condition
            # C is armed by multi-timeframe BB extremity; wait for a subsequent
            # completed 1m reversal candle and return inside its own BB.
            if armed[side] is not None:
                start=armed[side]
                confirm=(b['close']<b['open'] and obs[1] and b['close']<obs[1][1]) if short else (b['close']>b['open'] and obs[1] and b['close']>obs[1][2])
                if i>start and i-start<=5 and confirm:
                    name='bb_reversal_'+side.lower()
                    _add(results[name],name,side,bars,i,obs[1],'C BB extrem + subsequent 1M reversal')
                    armed[side]=None
                elif i-start>5:armed[side]=None
            if bb and (i==300 or not _extreme_at_previous(bars,i,side,bands)):
                armed[side]=i
            for kind,prefix in [('A','bb_only_'),('B','bb_rsi_'),('C','bb_reversal_')]:
                name=prefix+side.lower()
                checks[name]=[('BB ausserhalb 1M/5M/15M','green' if bb else 'neutral'),
                  ('RSI 1M/5M/15M Extrem (nur B)','green' if extreme else 'neutral'),
                  ('Umkehrkerze (nur C)','green' if kind=='C' and results[name] and results[name][-1]['time']==b['time'] else 'neutral')]
    return [tile(name,label,'green' if results[name] and results[name][-1]['time']==bars[-1]['time'] else 'neutral',
       'A BB / B BB+RSI / C BB mit bestätigter 1M-Umkehr; Einstieg nächste Kerze; Trailing-SL',results[name],checks[name])
       for name,label,_,_ in VARIANTS]

def _extreme_at_previous(bars,i,side,bands):
    time=bars[i-1]['time']+60
    for n in (1,5,15):
        times=[t for t in bands[n] if t<=time]
        if not times:return False
        close,upper,lower=bands[n][max(times)]
        if not (close>upper if side=='SHORT' else close<lower):return False
    return True

def _add(target,name,side,bars,i,one_min_band,reason):
    b=bars[i];entry=float(b['close']);recent=bars[max(0,i-4):i+1]
    stop=max(x['high'] for x in recent) if side=='SHORT' else min(x['low'] for x in recent)
    stop=max(stop,entry*1.001) if side=='SHORT' else min(stop,entry*.999)
    risk=abs(stop-entry);tp=entry-risk*2 if side=='SHORT' else entry+risk*2
    level=one_min_band[1] if side=='SHORT' else one_min_band[2]
    target.append(signal_with_params(name,side,b['time'],entry,stop,tp,reason,level,timeframe='1m'))
