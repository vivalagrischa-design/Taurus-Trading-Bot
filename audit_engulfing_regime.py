"""Read-only TAURUS REV_ENGULFING consistency/regime audit.

Usage:
 python audit_engulfing_regime.py v6.json v7.json --bars candles_5m.csv
CSV columns: market,time,open,high,low,close,volume; time=UTC epoch seconds.
No live orders and no mutation of paper databases.
"""
import argparse,csv,json,math,statistics
from collections import defaultdict
from datetime import datetime,timezone
from zoneinfo import ZoneInfo

CH=ZoneInfo('Europe/Zurich')
def trades(path):
    with open(path,encoding='utf-8') as f: data=json.load(f)
    if isinstance(data,dict):data=data.get('trades',[])
    return [t for t in data if t.get('strategy')=='rev_engulfing'
            and t.get('status')=='CLOSED' and isinstance(t.get('pnl'),(int,float))]

def candles(path):
    if not path:return {}
    out=defaultdict(list)
    with open(path,encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            m=r['market'].strip().lower()
            if m not in ('nq','mes','mgc'):continue
            out[m].append({k:(int(r[k]) if k=='time' else float(r[k])) for k in ('time','open','high','low','close','volume')})
    for m in out:out[m].sort(key=lambda x:x['time'])
    return out

def regime(market_bars,signal_time):
    """Only information from <= signal close; no future leakage."""
    hist=[b for b in market_bars if b['time']<=signal_time][-36:]
    if len(hist)<24:return None
    # Use last 12 completed 5M closes = 60M trend efficiency.
    tail=hist[-13:]
    closes=[x['close'] for x in tail]
    total=sum(abs(b-a) for a,b in zip(closes,closes[1:]))
    net=closes[-1]-closes[0]
    efficiency=abs(net)/total if total else 0
    true_ranges=[max(x['high']-x['low'],abs(x['high']-p['close']),abs(x['low']-p['close']))
                 for p,x in zip(hist[-15:-1],hist[-14:])]
    atr=sum(true_ranges)/len(true_ranges)
    recent=hist[-1]
    candle_range=max(recent['high']-recent['low'],1e-12)
    body=abs(recent['close']-recent['open'])/candle_range
    vol=[b['volume'] for b in hist[-21:-1] if b['volume']>0]
    volume_ratio=recent['volume']/statistics.median(vol) if vol and recent['volume']>0 else None
    # 0.35 is a hypothesis for research; never auto-block on this alone.
    state='TREND' if efficiency>=0.35 else 'CHOP'
    return dict(state=state,efficiency=round(efficiency,3),
                direction='UP' if net>0 else 'DOWN' if net<0 else 'FLAT',
                net_move=round(net,4),atr_5m=round(atr,4),
                candle_body_fraction=round(body,3),
                volume_ratio=round(volume_ratio,3) if volume_ratio is not None else None)

def audit(rows,market_bars):
    details=[]
    for t in rows:
        entry=t.get('entry')
        stop=t.get('initial_stop') or t.get('signal_stop')
        risk=abs(float(entry)-float(stop)) if entry is not None and stop is not None else None
        pnl=float(t['pnl'])
        reg=regime(market_bars.get(t['market'],[]),int(t['signal_time'])) if market_bars else None
        mfe=t.get('mfe_usd')
        risk_usd=t.get('risk_plan')
        stopout=pnl<0 and t.get('exit_reason')=='SL'
        details.append(dict(time_ch=datetime.fromtimestamp(int(t['signal_time']),timezone.utc).astimezone(CH).isoformat(),
            market=t['market'],side=t['side'],entry=entry,stop=stop,exit=t.get('exit'),
            exit_reason=t.get('exit_reason'),pnl=round(pnl,2),qty=t.get('qty'),
            planned_risk_usd=risk_usd,stop_distance=risk,
            mfe_usd=mfe,mae_usd=t.get('mae_usd'),trail_updates=t.get('trail_updates'),
            stopped_after_1r_intrabar=bool(stopout and isinstance(mfe,(int,float))
                and isinstance(risk_usd,(int,float)) and mfe>=risk_usd),
            regime=reg))
    groups=defaultdict(list)
    for d in details:
        groups['ALL'].append(d)
        groups['market:'+d['market']].append(d)
        groups['side:'+d['side']].append(d)
        groups['hour:'+d['time_ch'][11:13]].append(d)
        if d['regime']:
            groups['regime:'+d['regime']['state']].append(d)
            if d['regime']['state']=='TREND':
                groups['trend:'+d['regime']['direction']].append(d)
    summary={}
    for k,v in sorted(groups.items()):
        summary[k]=dict(n=len(v),wins=sum(x['pnl']>0 for x in v),
            win_rate=round(sum(x['pnl']>0 for x in v)/len(v),3),
            net_pnl=round(sum(x['pnl'] for x in v),2))
    return dict(summary=summary,trades=details,
                market_regime_available=bool(market_bars),
                caveat=None if market_bars else
                'Keine 5M-OHLCV-Kerzen geliefert: Marktbewegungen/Trend nicht vergleichbar. '
                'Zeit, Richtung, PnL und Exit sind aus dem Trade-Export analysierbar.')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('v6');p.add_argument('v7')
    p.add_argument('--bars',help='Optional 5M OHLCV CSV for BOTH periods')
    p.add_argument('--out',default='engulfing_regime_comparison.json')
    args=p.parse_args()
    m=candles(args.bars)
    a=audit(trades(args.v6),m)
    b=audit(trades(args.v7),m)
    result={'v6':a,'v7':b,'comparison':{'v6_trades':len(a['trades']),
        'v7_trades':len(b['trades']),
        'same_rules_not_same_trades':True,
        'regime_comparison_valid':bool(m and all(d['regime'] for d in a['trades']+b['trades'])),
        'important':'Compare win rate AND normalized R, session, side, market, '
                    'ATR, trend efficiency. Small samples are inconclusive. '
                    'Do not apply a session or trend filter until out-of-sample verified.'}}
    with open(args.out,'w',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'v6':a['summary'].get('ALL'),'v7':b['summary'].get('ALL'),
          'regime_comparison_valid':result['comparison']['regime_comparison_valid'],
          'output':args.out},ensure_ascii=False))
if __name__=='__main__':main()
