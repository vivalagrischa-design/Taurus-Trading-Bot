"""PO3 10:00-Modell (Power of 3 / AMD) – Forward-Test im TAURUS LAB.

Herkunft: Checkliste "The FULL PO3 Checklist" (J. Gretzema), in feste Regeln
uebersetzt und auf SPY-1M-Daten 2010-04/2026 getestet (Variante 3R +
Volatilitaetsfilter: n=519, +0.12 R nach Kosten, 95%-KI -0.02..+0.29 R).
Die Variante wurde NACH Sicht auf alle Jahre gewaehlt -> dieser Forward-Test
ist die eigentliche Pruefung. Regeln deshalb NICHT nachoptimieren.

Regeln (Long; Short gespiegelt), alle Zeiten New York:
 0 Volatilitaet : ATR14 (Index-Tageskerzen, bis Vortag) liegt im Rang >= 33 %
                  der letzten 250 Tage  -> an ruhigen Tagen kein Handel
 1 Bias         : Vortag 09:30-16:00 bullisch UND 4H-Kerze 06:00-10:00 bullisch
 2 HTF-PDA      : vor dem Entry wurde seit 04:00 das Vortagestief gesweept ODER
                  in ein offenes bullisches 4H-FVG der letzten 10 Tage getappt
 3 Accumulation : Range 09:30-10:00 <= 0.35 * ATR14 (ATR in % vom Index,
                  umgerechnet auf den Futures-Kurs)
 4 Manipulation : ab 10:00 Sweep unter das Accumulation-Tief ODER Tap in ein
                  bullisches 5M-FVG, das nach 10:00 entstanden ist
 5 Entry        : bis 12:00 – 1M-IFVG (Schluss ueber dem Top des letzten
                  bearishen 1M-FVG seit Manipulationsbeginn), sonst BOS
                  (Schluss ueber dem letzten 1M-Swing-High vor dem Tief)
 Risiko         : Stop = Manipulations-Tief - 2 Ticks, Ziel 3R, kein Trailing,
                  Zeit-Ausstieg 15:55. Max. 1 Trade pro Tag.

Nur abgeschlossene Kerzen, kein Lookahead. Tagesdaten (Index) kommen aus einem
Cache, den main.paper_loop ueber refresh_daily() fuellt; ohne Cache keine Signale.
"""
import time
from bisect import bisect_left
from datetime import datetime, timedelta, timezone
from threading import Lock
from zoneinfo import ZoneInfo

from strategies import tile, signal_with_params

NY = ZoneInfo('America/New_York')
ID = 'po3_10am'
NAME = 'PO3 10:00 (Power of 3, 3R)'
VERSION = 'po3_10am_v1_20261106'
MARKETS = ('nq', 'mes')
INDEX = {'nq': '^NDX', 'mes': '^GSPC'}
TICK = {'nq': 0.25, 'mes': 0.25}

ACC_K = 0.35
VOL_MIN_RANK = 0.33
TARGET_R = 3.0
ENTRY_END = 12 * 60
TIME_EXIT = 15 * 60 + 55
MIN_RISK_PCT = 0.0001
BUFFER_TICKS = 2
DAILY_REFRESH_SECONDS = 6 * 3600

_DAILY = {}          # market -> {'rows': [(date, o, h, l, c)], 'fetched': ts, 'error': str|None}
_LOCK = Lock()


# ----------------------------------------------------------------- Tagesdaten
def set_daily(market, rows):
    """rows: [(datetime.date, open, high, low, close)] aufsteigend (Tests/Fallback)."""
    _DAILY[market] = {'rows': sorted(rows), 'fetched': time.time(), 'error': None}


def refresh_daily(market, force=False):
    """Index-Tageskerzen (2 Jahre) holen; hoechstens alle 6 Stunden."""
    if market not in INDEX:
        return None
    with _LOCK:
        cur = _DAILY.get(market)
        if cur and not force and time.time() - cur['fetched'] < DAILY_REFRESH_SECONDS:
            return cur
        try:
            import yfinance as yf
            frame = yf.Ticker(INDEX[market]).history(period='2y', interval='1d', auto_adjust=False, timeout=12)
            rows = []
            for idx, r in frame.iterrows():
                o, h, l, c = (float(r[k]) for k in ('Open', 'High', 'Low', 'Close'))
                if l <= min(o, c) <= max(o, c) <= h:
                    rows.append((idx.date(), o, h, l, c))
            if len(rows) < 120:
                raise RuntimeError(f'nur {len(rows)} Tageskerzen')
            set_daily(market, rows)
        except Exception as exc:
            _DAILY[market] = dict(cur or {'rows': []}, fetched=time.time(), error=str(exc)[:160])
        return _DAILY[market]


def daily_context(market, day):
    """ATR14 (in % des Schlusskurses) und ATR-Rang, beides nur bis zum Vortag von `day`."""
    rows = [r for r in (_DAILY.get(market) or {}).get('rows', []) if r[0] < day]
    if len(rows) < 120:
        return None
    trs = []
    for i in range(1, len(rows)):
        _, _, h, l, _ = rows[i]
        pc = rows[i - 1][4]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    atrs = [sum(trs[i - 13:i + 1]) / 14 for i in range(13, len(trs))]
    window = atrs[-250:]
    atr = atrs[-1]
    rank = sum(1 for a in window if a <= atr) / len(window)
    return {'atr_pct': atr / rows[-1][4], 'rank': rank}


# ----------------------------------------------------------------- Hilfen
def _ny(ts):
    return datetime.fromtimestamp(int(ts), timezone.utc).astimezone(NY)


def _epoch(day, minute):
    dt = datetime(day.year, day.month, day.day, minute // 60, minute % 60, tzinfo=NY)
    return int(dt.timestamp())


def _four_hour(bars, until_ts):
    """4H-Kerzen im Futures-Raster (02/06/10/14/18/22 NY), nur abgeschlossene."""
    out = {}
    for b in bars:
        if b['time'] >= until_ts:
            break
        dt = _ny(b['time'])
        start = dt.replace(minute=0, second=0, microsecond=0) - timedelta(hours=(dt.hour - 2) % 4)
        key = int(start.timestamp())
        x = out.get(key)
        if x is None:
            out[key] = dict(time=key, open=b['open'], high=b['high'], low=b['low'], close=b['close'])
        else:
            x['high'] = max(x['high'], b['high']); x['low'] = min(x['low'], b['low']); x['close'] = b['close']
    candles = [out[k] for k in sorted(out)]
    return [c for c in candles if c['time'] + 4 * 3600 <= until_ts]


def _fvg_zones(h4, d, ready_until, ready_from):
    zones = []
    for i in range(2, len(h4)):
        ready = h4[i]['time'] + 4 * 3600
        if not ready_from <= ready <= ready_until:
            continue
        if d == 1 and h4[i]['low'] > h4[i - 2]['high']:
            zones.append((h4[i - 2]['high'], h4[i]['low']))
        if d == -1 and h4[i]['high'] < h4[i - 2]['low']:
            zones.append((-h4[i - 2]['low'], -h4[i]['high']))     # gespiegelt
    return zones


def _five_min_fvgs(day_bars, d):
    """Bullische (gespiegelt) 5M-FVGs aus Kerzen ab 10:00: (fertig_ab_minute, unten, oben)."""
    buckets = {}
    for t, b in day_bars:
        if t < 600:
            continue
        k = t - t % 5
        x = buckets.get(k)
        if x is None:
            buckets[k] = [b['high'], b['low']]
        else:
            x[0] = max(x[0], b['high']); x[1] = min(x[1], b['low'])
    keys = sorted(buckets)
    hh = [buckets[k][0] if d == 1 else -buckets[k][1] for k in keys]
    ll = [buckets[k][1] if d == 1 else -buckets[k][0] for k in keys]
    out = []
    for i in range(2, len(keys)):
        if ll[i] > hh[i - 2]:
            out.append((keys[i] + 5, hh[i - 2], ll[i]))
    return out


# ----------------------------------------------------------------- Tageslogik
def _scan_day(market, day, day_bars, prev, h4_6, h4all, ctx, status):
    """day_bars: [(minute, bar)] 04:00-16:00 des Tages. Gibt Signal oder None."""
    # 1 Bias
    prev_bull = prev['close'] > prev['open']
    h4_bull = h4_6['close'] > h4_6['open']
    if prev_bull and h4_bull:
        d = 1
    elif not prev_bull and not h4_bull:
        d = -1
    else:
        status['bias'] = 'red'
        return None
    status['bias'] = 'green'
    # 0 Volatilitaet
    if ctx['rank'] < VOL_MIN_RANK:
        status['vola'] = 'red'
        return None
    status['vola'] = 'green'
    # 3 Accumulation
    acc = [b for t, b in day_bars if 570 <= t < 600]
    if len(acc) < 20:
        status['acc'] = 'neutral'
        return None
    a_hi = max(b['high'] for b in acc); a_lo = min(b['low'] for b in acc)
    ref = acc[-1]['close']
    if (a_hi - a_lo) > ACC_K * ctx['atr_pct'] * ref:
        status['acc'] = 'red'
        return None
    status['acc'] = 'green'

    t = [m for m, _ in day_bars]
    if d == 1:
        h = [b['high'] for _, b in day_bars]; l = [b['low'] for _, b in day_bars]
        c = [b['close'] for _, b in day_bars]
        acc_lo, pdl = a_lo, prev['low']
    else:
        h = [-b['low'] for _, b in day_bars]; l = [-b['high'] for _, b in day_bars]
        c = [-b['close'] for _, b in day_bars]
        acc_lo, pdl = -a_hi, -prev['high']
    n = len(t)
    i10 = bisect_left(t, 600)
    ten = _epoch(day, 600)
    zones = _fvg_zones(h4all, d, ten, ten - 10 * 86400)
    fvg5 = _five_min_fvgs(day_bars, d)

    def htf_tapped(upto):
        lo = min(l[:upto + 1])
        if lo <= pdl:
            return True
        return any(lo <= top and lo >= bot - (top - bot) for bot, top in zones)

    manip_i = None; bear_fvgs = []; swing_highs = []
    for i in range(i10, n):
        if t[i] >= ENTRY_END:
            break
        if manip_i is None:
            sweep = l[i] < acc_lo
            ftap = any(t[i] >= rt and bot <= l[i] <= top for rt, bot, top in fvg5)
            if sweep or ftap:
                manip_i = i
                status['manip'] = 'green'
                j0 = bisect_left(t, 570)
                swing_highs = [(j, h[j]) for j in range(j0 + 1, i) if h[j] > h[j - 1] and h[j] >= h[j + 1]]
            continue
        if i - 2 >= manip_i - 2 and h[i] < l[i - 2]:
            bear_fvgs.append(l[i - 2])
        if i - 2 >= manip_i and h[i - 1] > h[i - 2] and h[i - 1] >= h[i]:
            swing_highs.append((i - 1, h[i - 1]))
        trig = None
        if bear_fvgs and c[i] > bear_fvgs[-1]:
            trig = 'IFVG'
        else:
            seg = l[manip_i:i + 1]
            imin = manip_i + seg.index(min(seg))
            sh = [lv for j, lv in swing_highs if j < imin]
            if sh and c[i] > sh[-1]:
                trig = 'BOS'
        if trig is None or not htf_tapped(i):
            continue
        status['htf'] = 'green'
        buffer = BUFFER_TICKS * TICK.get(market, 0.25)
        entry = c[i]
        stop = min(l[manip_i:i + 1]) - buffer
        risk = entry - stop
        if risk < MIN_RISK_PCT * abs(entry):
            continue
        tp = entry + TARGET_R * risk
        bar = day_bars[i][1]
        side = 'LONG' if d == 1 else 'SHORT'
        sgn = 1 if d == 1 else -1
        sig = signal_with_params(ID, side, bar['time'], sgn * entry, sgn * stop, sgn * tp,
                                 f'PO3 10:00 {side}: {trig}-Entry nach Manipulation, Ziel 3R, Ausstieg 15:55',
                                 level=a_lo if d == 1 else a_hi, timeframe='1m')
        sig['time_exit'] = _epoch(day, TIME_EXIT)
        sig['version'] = VERSION
        sig['trigger'] = trig
        status['entry'] = 'green'
        return sig
    return None


def build(bars1m, market='nq', last_only=False):
    checks_labels = [('vola', 'Volatilität ≥ 33 %-Rang'), ('bias', 'Bias Vortag + 4H 06–10'),
                     ('acc', 'Accumulation 09:30–10:00 eng'), ('manip', 'Manipulation ab 10:00'),
                     ('htf', 'HTF-Level getappt'), ('entry', 'Entry IFVG/BOS bis 12:00')]

    def done(state, details, signals, status):
        checks = [(label, status.get(key, 'neutral')) for key, label in checks_labels]
        return tile(ID, NAME, state, details, signals, checks)

    if market not in MARKETS:
        return done('neutral', 'Nur für MNQ und MES (US-Index-Futures).', [], {})
    if not (_DAILY.get(market) or {}).get('rows'):
        return done('neutral', 'Wartet auf Index-Tagesdaten (Volatilitätsfilter).', [], {})
    bars = sorted(bars1m or [], key=lambda b: b['time'])
    if len(bars) < 300:
        return done('neutral', 'Zu wenige 1M-Kerzen.', [], {})

    sessions = {}
    for b in bars:
        dt = _ny(b['time'])
        sessions.setdefault(dt.date(), []).append((dt.hour * 60 + dt.minute, b))
    days = sorted(sessions)
    rth_days = [dd for dd in days if sum(1 for m, _ in sessions[dd] if 570 <= m < 960) >= 200]
    targets = days[-1:] if last_only else days
    signals = []; status = {}; details = 'Wartet auf 10:00 New York'
    for day in targets:
        status = {}
        rows = [(m, b) for m, b in sessions[day] if 240 <= m < 960]
        prevs = [dd for dd in rth_days if dd < day]
        if not prevs or not any(570 <= m < 600 for m, _ in rows):
            continue
        prow = [b for m, b in sessions[prevs[-1]] if 570 <= m < 960]
        prev = dict(open=prow[0]['open'], close=prow[-1]['close'],
                    high=max(b['high'] for b in prow), low=min(b['low'] for b in prow))
        ten = _epoch(day, 600)
        h4all = _four_hour(bars, ten)
        h4_6 = next((x for x in h4all if x['time'] == ten - 4 * 3600), None)
        ctx = daily_context(market, day)
        if h4_6 is None or ctx is None:
            continue
        sig = _scan_day(market, day, rows, prev, h4_6, h4all, ctx, status)
        if sig:
            signals.append(sig)
            details = f"Signal {sig['side']} ({sig['trigger']})"
        else:
            reds = [label for key, label in checks_labels if status.get(key) == 'red']
            details = ('Kein Setup: ' + reds[0]) if reds else 'Setup läuft / kein Entry'
    if not signals and status == {}:
        details = 'Wartet auf 10:00 New York'
    recent = bool(signals and signals[-1]['time'] == bars[-1]['time'])
    state = 'green' if recent else 'yellow' if status.get('manip') == 'green' else 'neutral'
    return done(state, details, signals, status)
