"""Objective, research-only Market Map setups inspired by the supplied video.
Assumptions are explicit because the video's proprietary day-classification map is not specified.
Signals are generated on completed 5m bars; no existing strategy/execution rules are changed.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

NY=ZoneInfo("America/New_York")

def _dt(ts):
    return datetime.fromtimestamp(int(ts),timezone.utc).astimezone(NY)

def _sig(name,side,b,stop,reason,level):
    entry=float(b["close"]); risk=abs(entry-stop)
    if risk<=0:return None
    target=entry+(2*risk if side=="LONG" else -2*risk)
    return {"id":f"{name}-{int(b['time'])}","strategy":name,"time":int(b["time"]),
      "side":side,"entry":round(entry,5),"stop":round(stop,5),"tp":round(target,5),
      "level":round(float(level),5),"breakout_time":int(b["time"]),
      "status":"HISTORISCHES TESTSIGNAL","reason":reason,"timeframe":"5m"}

def build(bars):
    """Four objective patterns: Tokyo range continuation, prior-day reversal,
    Tokyo sweep/reversal, previous-day high/low liquidity sweep."""
    if len(bars)<100:return []
    days={}
    for i,b in enumerate(bars):
        d=_dt(b["time"]).date().isoformat()
        days.setdefault(d,[]).append((i,_dt(b["time"]),b))
    keys=sorted(days)
    found={k:[] for k in ("map_tokyo_breakout","map_yday_reversal","map_tokyo_sweep","map_yday_sweep")}
    checks={k:[] for k in found}
    for di,day in enumerate(keys):
        rows=days[day]
        # The video's first four Tokyo hours: 19:00–23:00 New York (proxy).
        tokyo=[x for x in rows if x[1].hour>=19 or x[1].hour<1]
        if len(tokyo)<24:continue
        th=max(float(x[2]["high"]) for x in tokyo); tl=min(float(x[2]["low"]) for x in tokyo)
        active=[x for x in rows if x[1].hour>=3 and x[1].hour<16]
        if not active:continue
        prev=days[keys[di-1]] if di>0 else []
        pdh=max(float(x[2]["high"]) for x in prev) if prev else None
        pdl=min(float(x[2]["low"]) for x in prev) if prev else None
        # Prior day's candle body range: previous session open/close; reversal at its extremes.
        p_hi=max(float(x[2]["high"]) for x in prev) if prev else None
        p_lo=min(float(x[2]["low"]) for x in prev) if prev else None
        mode={k:False for k in found}; prevclose=None
        for pos,(i,dt,b) in enumerate(active):
            c=float(b["close"]); h=float(b["high"]); l=float(b["low"])
            # Continuation: close breaks Tokyo range then next bar retests boundary and holds.
            if pos and pos+1<len(active):
                p=active[pos-1][2]; n=active[pos+1][2]
                if float(p["close"])<=th<c and float(n["low"])<=th and float(n["close"])>th and not mode["map_tokyo_breakout"]:
                    s=_sig("map_tokyo_breakout","LONG",n,min(float(p["low"]),float(n["low"])),"Tokyo-range break and hold retest",th)
                    if s:found["map_tokyo_breakout"].append(s)
                    mode["map_tokyo_breakout"]=True
                if float(p["close"])>=tl>c and float(n["high"])>=tl and float(n["close"])<tl and not mode["map_tokyo_breakout"]:
                    s=_sig("map_tokyo_breakout","SHORT",n,max(float(p["high"]),float(n["high"])),"Tokyo-range breakdown and hold retest",tl)
                    if s:found["map_tokyo_breakout"].append(s)
                    mode["map_tokyo_breakout"]=True
            # Sweep: pierce a fixed level then close back through it.
            if not mode["map_tokyo_sweep"] and h>th and c<th:
                s=_sig("map_tokyo_sweep","SHORT",b,h,"Sweep above Tokyo high, close back inside",th)
                if s:found["map_tokyo_sweep"].append(s)
                mode["map_tokyo_sweep"]=True
            elif not mode["map_tokyo_sweep"] and l<tl and c>tl:
                s=_sig("map_tokyo_sweep","LONG",b,l,"Sweep below Tokyo low, close back inside",tl)
                if s:found["map_tokyo_sweep"].append(s)
                mode["map_tokyo_sweep"]=True
            if pdh is not None and not mode["map_yday_sweep"]:
                if h>pdh and c<pdh:
                    s=_sig("map_yday_sweep","SHORT",b,h,"Sweep previous-day high and close back below",pdh)
                    if s:found["map_yday_sweep"].append(s)
                    mode["map_yday_sweep"]=True
                elif l<pdl and c>pdl:
                    s=_sig("map_yday_sweep","LONG",b,l,"Sweep previous-day low and close back above",pdl)
                    if s:found["map_yday_sweep"].append(s)
                    mode["map_yday_sweep"]=True
            # Prior-day level reversal after touch and rejection.
            if p_hi is not None and not mode["map_yday_reversal"]:
                if h>=p_hi and c<p_hi:
                    s=_sig("map_yday_reversal","SHORT",b,h,"Reject previous-day high",p_hi)
                    if s:found["map_yday_reversal"].append(s)
                    mode["map_yday_reversal"]=True
                elif l<=p_lo and c>p_lo:
                    s=_sig("map_yday_reversal","LONG",b,l,"Reject previous-day low",p_lo)
                    if s:found["map_yday_reversal"].append(s)
                    mode["map_yday_reversal"]=True
    labels={"map_tokyo_breakout":"Market Map · Tokyo Breakout/Retest","map_yday_reversal":"Market Map · Yesterday Reversal","map_tokyo_sweep":"Market Map · Tokyo Stop Sweep","map_yday_sweep":"Market Map · Yesterday Liquidity Sweep"}
    return [{"id":k,"name":labels[k],"state":"neutral","details":"Feste Levels · Forschungsregel · 5m · einmal je Setup/Tag","signals":found[k][::-1],"checks":[("Regelbedingung erfüllt","green" if found[k] else "neutral")]} for k in found]
