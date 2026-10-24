const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const PORT = Number(process.env.PORT || 10000);
const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, 'data');
const STORE = path.join(DATA_DIR, 'signals.json');
const CONFIG = path.join(DATA_DIR, 'risk-config.json');
const TOKEN = process.env.WEBHOOK_TOKEN || '';
fs.mkdirSync(DATA_DIR, { recursive: true });
if (!fs.existsSync(STORE)) fs.writeFileSync(STORE, '[]');
const DEFAULT_CONFIG = { manualMllRemaining: 2000, mllReserve: 1000, maxRiskPerTrade: 50, dailyLossStop: 200, maxContracts: 1, commissionPerSide: 0.5 };
if (!fs.existsSync(CONFIG)) fs.writeFileSync(CONFIG, JSON.stringify(DEFAULT_CONFIG));

function readSignals() {
  try { return JSON.parse(fs.readFileSync(STORE, 'utf8')); } catch { return []; }
}
function writeSignals(rows) {
  const tmp = STORE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(rows));
  fs.renameSync(tmp, STORE);
}
function readConfig() { try { return { ...DEFAULT_CONFIG, ...JSON.parse(fs.readFileSync(CONFIG, 'utf8')) }; } catch { return { ...DEFAULT_CONFIG }; } }
function writeConfig(config) { fs.writeFileSync(CONFIG, JSON.stringify(config)); }
function dayKey(ms) { return new Intl.DateTimeFormat('en-CA', {timeZone:'Europe/Zurich',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(ms)); }
function closedToday(rows, now=Date.now()) { const key=dayKey(now); return rows.filter(r=>r.closedTime && dayKey(r.closedTime)===key).reduce((s,r)=>s+(Number(r.netPnl)||0),0); }
function send(res, status, body, type='application/json; charset=utf-8') {
  res.writeHead(status, { 'content-type': type, 'cache-control': 'no-store' });
  res.end(body);
}
function esc(v) { return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  if (req.method === 'GET' && url.pathname === '/api/config') return send(res, 200, JSON.stringify(readConfig()));
  if (req.method === 'POST' && url.pathname === '/api/config') {
    let raw=''; req.on('data', c => { raw+=c; if(raw.length>4000) req.destroy(); });
    req.on('end', () => { try { const x=JSON.parse(raw), config={
      manualMllRemaining: Math.max(0, Number(x.manualMllRemaining)), mllReserve: Math.max(0, Number(x.mllReserve)),
      maxRiskPerTrade: Math.max(1, Number(x.maxRiskPerTrade)), dailyLossStop: Math.max(1, Number(x.dailyLossStop)),
      maxContracts: Math.max(1, Math.min(100, Math.floor(Number(x.maxContracts)))), commissionPerSide: Math.max(0, Number(x.commissionPerSide))
    }; if(Object.values(config).some(v=>!Number.isFinite(v))) return send(res,400,'{"error":"invalid config"}'); writeConfig(config); send(res,200,JSON.stringify(config)); } catch { send(res,400,'{"error":"bad json"}'); } }); return;
  }
  if (req.method === 'GET' && url.pathname === '/api/signals') {
    const rows=readSignals().sort((a,b) => b.signalTime - a.signalTime); return send(res, 200, JSON.stringify({rows, config:readConfig(), dailyNet:closedToday(rows)}));
  }
  if (req.method === 'POST' && url.pathname === '/webhook') {
    let raw = ''; req.on('data', chunk => { raw += chunk; if (raw.length > 16000) req.destroy(); });
    req.on('end', () => {
      try {
        const msg = JSON.parse(raw);
        const supplied=Buffer.from(String(msg.token||'')), expected=Buffer.from(TOKEN);
        if (!TOKEN || supplied.length!==expected.length || !crypto.timingSafeEqual(supplied, expected)) return send(res, 401, '{"error":"unauthorized"}');
        if (!['entry','followup'].includes(msg.event) || !msg.signalId || !['MNQ','MES'].includes(msg.symbol)) return send(res, 400, '{"error":"invalid payload"}');
        const rows = readSignals();
        if (msg.event === 'entry') {
          const prior = rows.find(r => r.signalId === msg.signalId);
          if (!prior) {
            const cfg=readConfig(), now=Number(msg.time)||Date.now(), side=msg.side==='SHORT'?'SHORT':'LONG', pointValue=msg.symbol==='MNQ'?2:5;
            const entry=Number(msg.entry), stop=Number(msg.stop), target=Number(msg.target), contracts=Math.min(cfg.maxContracts,Math.max(1,Math.floor(Number(msg.contracts)||1)));
            const risk= Math.abs(entry-stop)*pointValue*contracts + cfg.commissionPerSide*2*contracts;
            const dayPnl=closedToday(rows,now), openRisk=rows.filter(r=>r.state==='Beobachtung'&&!r.blocked).reduce((sum,r)=>sum+(Number(r.plannedRisk)||0),0), mllRemainingNow=cfg.manualMllRemaining+Math.min(0,dayPnl)-openRisk, reason=risk>cfg.maxRiskPerTrade?'Risiko je Trade überschritten':dayPnl-openRisk-risk < -cfg.dailyLossStop?'Tagesverlust-Stopp würde überschritten':mllRemainingNow-risk < cfg.mllReserve?'MLL-Sicherheitsreserve würde unterschritten':'';
            rows.push({ signalId: msg.signalId, signalTime: now, symbol: msg.symbol, side, trend: msg.trend, level: Number(msg.level), entry, stop, target, contracts, pointValue, plannedRisk:risk, state: reason?`Gesperrt · ${reason}`:'Beobachtung', candles: [], note: reason, blocked:Boolean(reason) });
          }
        } else {
          const row = rows.find(r => r.signalId === msg.signalId);
          if (row) {
            if (Number.isFinite(Number(msg.stop)) && Number(msg.stop)>0) row.stop=Number(msg.stop);
            const n = Number(msg.n);
            if (n >= 1 && n <= 5 && !row.candles.some(c => c.n === n)) row.candles.push({n, dir: msg.dir, time: Number(msg.time) || Date.now()});
            row.candles.sort((a,b) => a.n-b.n);
            if (msg.exit === 'stop' || msg.exit === 'target') {
              row.exitPrice=Number(msg.exitPrice); row.closedTime=Number(msg.time)||Date.now();
              row.netPnl=(row.side==='LONG'?row.exitPrice-row.entry:row.entry-row.exitPrice)*row.pointValue*row.contracts-readConfig().commissionPerSide*2*row.contracts;
              row.state=msg.exit==='stop'?'Stop':'Ziel';
            }
            else if (row.candles.length >= 5) row.state = '5 Kerzen abgeschlossen';
          }
        }
        writeSignals(rows.slice(-1000)); send(res, 200, '{"ok":true}');
      } catch { send(res, 400, '{"error":"bad json"}'); }
    });
    return;
  }
  if (req.method === 'GET' && (url.pathname === '/' || url.pathname === '/index.html')) {
    return send(res, 200, fs.readFileSync(path.join(__dirname, 'index.html')), 'text/html; charset=utf-8');
  }
  send(res, 404, 'not found', 'text/plain; charset=utf-8');
});
server.listen(PORT, '0.0.0.0', () => console.log(`Scanner dashboard listening on ${PORT}`));
