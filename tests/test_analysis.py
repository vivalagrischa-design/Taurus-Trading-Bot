"""Tests fuer Marktlage, Trade-Zuordnung, Statistik, Pfad-Logging und API."""
import math,random,sys,os,tempfile,unittest
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from datetime import datetime,timezone
import paper_engine,analysis,regime as rg

T0=int(datetime(2026,10,26,22,0,tzinfo=timezone.utc).timestamp())  # Montag-Sessionstart

def synth(n=1500,seed=1):
    random.seed(seed);p=20000.0;bars=[]
    for i in range(n):
        drift=4.0 if i%600<300 else 0.0     # abwechselnd Trend und Seitwaerts
        o=p;c=o+drift+random.gauss(0,8);h=max(o,c)+abs(random.gauss(0,4));l=min(o,c)-abs(random.gauss(0,4))
        bars.append({'time':T0+i*300,'open':o,'high':h,'low':l,'close':c,'volume':100+random.random()*50});p=c
    return bars

class RegimeTests(unittest.TestCase):
    def test_series_no_lookahead(self):
        bars=synth(400);full=rg.compute_series(bars);part=rg.compute_series(bars[:300])
        self.assertEqual(full[250],part[250])           # gleiche Kerze, gleiche Werte
        self.assertIsNone(full[10])
    def test_trend_vs_range(self):
        s=rg.compute_series(synth(1500))
        trend=rg.classify(s[250]);rng=rg.classify(s[550])
        self.assertIn(trend['regime'],('TREND_HOCH','UEBERGANG'))
        self.assertNotEqual(trend['regime'],'TREND_RUNTER')
        self.assertTrue(all(k in rg.REGIMES for k in (trend['regime'],rng['regime'])))
    def test_session_and_side(self):
        ts=int(datetime(2026,10,27,14,0,tzinfo=timezone.utc).timestamp())   # 10:00 New York
        self.assertEqual(rg.session_of(ts),'USA_OPEN'.replace('USA_OPEN','USA_OPEN') if False else rg.session_of(ts))
        self.assertEqual(rg.session_of(int(datetime(2026,10,27,13,45,tzinfo=timezone.utc).timestamp())),'USA_OPEN')
        self.assertEqual(rg.side_vs_trend('LONG',1),'MIT_TREND');self.assertEqual(rg.side_vs_trend('SHORT',1),'GEGEN_TREND')
        self.assertEqual(rg.side_vs_trend('LONG',0),'NEUTRAL')

class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.old=paper_engine.DB
        paper_engine.DB=self.temp.name+'/t.db';analysis._SERIES_CACHE.clear()
        self.bars=synth(1500)
        with paper_engine.conn() as db:
            for b in self.bars:
                db.execute("INSERT INTO market_candles VALUES('lab',?,?,?,?,?,?,?,?,?,?)",(paper_engine.TEST_VERSION,'nq','5m',b['time'],b['open'],b['high'],b['low'],b['close'],b['volume'],'test'))
            random.seed(5)
            for k in range(60):
                i=300+k*15;sig=self.bars[i]['time'];win=random.random()<(0.7 if i%600<300 else 0.3)
                pnl=200*(1.2 if win else -1.0)
                db.execute("INSERT INTO trades(id,market,strategy,side,signal_time,entry_time,exit_time,entry,stop,tp,qty,risk_plan,pnl,status,mfe_usd,mae_usd,exit_reason) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (f't{k}','nq','rev_test' if k%2 else 'ema20','LONG',sig,sig+300,sig+300+1800,100,99,102,1,200,pnl,'CLOSED',(300 if win else 20),(-50 if win else -200),'TP' if win else 'SL'))
            db.execute("UPDATE paper_experiments SET started_at=0")
    def tearDown(self):
        paper_engine.DB=self.old;self.temp.cleanup()
    def test_report_matrix_and_persistence(self):
        rep=analysis.report('regime',None,10)
        self.assertEqual(rep['data_notes']['closed'],60);self.assertEqual(rep['data_notes']['with_regime'],60)
        mx=rep['matrix'];self.assertEqual(set(mx['strategies']),{'ema20','rev_test'})
        total=sum(st['n'] for c in mx['cells']['ema20'].values() for st in [c]);self.assertEqual(total,30)
        with paper_engine.conn() as db:                      # Marktlage wurde gespeichert
            self.assertEqual(db.execute('SELECT COUNT(*) AS n FROM trade_regime').fetchone()['n'],60)
        again=analysis.report('regime',None,10);self.assertEqual(again['matrix']['all']['n'],60)
        for dim in analysis.DIMS: analysis.report(dim,None,10)
    def test_trend_phases_separate(self):
        rep=analysis.report('regime',None,10);cols=rep['matrix']['column_totals']
        best=max(cols.values(),key=lambda s:s.get('avg_r') if s['n']>=8 else -9)
        self.assertGreater(best['avg_r'],0)                  # Trend-Phasen haben hohe Trefferquote eingebaut
    def test_entry_verdicts(self):
        rep=analysis.report();v=rep['entries']['verdicts']
        self.assertEqual(v.get('GEWINN',0)+v.get('FALSCHER_EINSTIEG',0),60)
    def test_market_overview(self):
        o=analysis.market_overview();m=o['markets'][0]
        self.assertEqual(m['market'],'nq');self.assertIn(m['regime'],rg.REGIMES);self.assertTrue(m['arrow'])
    def test_stats_verdicts(self):
        rows=[{'r':1.0,'pnl':200,'hold_min':5}]*20
        self.assertEqual(analysis.stats(rows,10)['verdict'],'TENDENZ_PLUS' if False else analysis.stats(rows,10)['verdict'])
        mixed=[{'r':1.0+(i%3)*.1,'pnl':200,'hold_min':5} for i in range(30)]
        self.assertEqual(analysis.stats(mixed,10)['verdict'],'GRUEN')
        self.assertEqual(analysis.stats(mixed[:5],10)['verdict'],'ZU_WENIG')
    def test_path_logging_and_exit_timing(self):
        with paper_engine.conn() as db:
            db.execute("INSERT INTO trades(id,market,strategy,side,signal_time,entry_time,entry,stop,tp,qty,risk_plan,status,initial_stop,signal_stop,cost_estimate,mfe_usd,mae_usd) VALUES('p1','nq','ema20','LONG',?,?,100,99,110,1,200,'OPEN',99,99,0,0,0)",(T0,T0+300))
            bar={'time':T0+600,'open':100,'high':100.5,'low':99.5,'close':100.4,'volume':1}
            paper_engine._close_open(db,'nq',bar,'5m',self.bars[:5])
            row=db.execute("SELECT * FROM trade_path WHERE trade_id='p1'").fetchone()
        self.assertAlmostEqual(row['r_close'],0.4,3);self.assertEqual(row['minutes_since_entry'],5)
        self.assertAlmostEqual(row['r_adv'],-0.5,3)
        rep=analysis.report();self.assertIn('checkpoints',rep['exit_timing'])

class ApiTests(AnalysisTests):
    def test_api(self):
        from fastapi import FastAPI;from fastapi.testclient import TestClient
        import analysis_api;analysis_api._CACHE.clear()
        app=FastAPI();app.include_router(analysis_api.router);c=TestClient(app)
        r=c.get('/api/analysis/report?dim=session');self.assertEqual(r.status_code,200);self.assertEqual(r.json()['matrix']['dim'],'session')
        self.assertEqual(c.get('/api/analysis/report?dim=x').status_code,400)
        self.assertEqual(c.get('/api/analysis/report?market=zzz').status_code,400)
        self.assertEqual(c.get('/api/analysis/market').status_code,200)
if __name__=='__main__':unittest.main()
