"""TAURUS Marktlage (Regime) - rein aus abgeschlossenen 5M-Kerzen berechnet.

Kein Lookahead: Die Kennzahlen bei Kerze i benutzen nur Kerzen <= i.
Dieselbe Funktion dient fuer
  * die Live-Anzeige (Seite 1) und
  * die nachtraegliche Zuordnung jedes Trades zu seiner Marktlage (Backfill).
Reine Python-Standardbibliothek, keine zusaetzlichen Pakete noetig.
"""
import math
from bisect import bisect_left, bisect_right, insort
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

FEATURE_VERSION = 'regime_v1'
STEP = 300                      # 5M-Kerze in Sekunden
WARMUP = 60                     # Kerzen, bevor Kennzahlen gueltig sind
PCT_MIN_HISTORY = 200           # Mindestverlauf fuer Perzentile (ATR, BB-Breite)
NY = ZoneInfo('America/New_York')
ZH = ZoneInfo('Europe/Zurich')

REGIMES = ('TREND_HOCH', 'TREND_RUNTER', 'RANGE', 'CHOP', 'UEBERGANG', 'UNBEKANNT')
ARROWS = {'TREND_HOCH': '↑', 'TREND_RUNTER': '↓', 'RANGE': '→', 'CHOP': '↕'}


def _ema(values, period):
    out = [None] * len(values)
    if len(values) < period:
        return out
    k = 2.0 / (period + 1)
    prev = sum(values[:period]) / period
    out[period - 1] = prev
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def _rsi(closes, period=14):
    out = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains = [max(0.0, closes[i] - closes[i - 1]) for i in range(1, len(closes))]
    losses = [max(0.0, closes[i - 1] - closes[i]) for i in range(1, len(closes))]
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    out[period] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for j in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[j]) / period
        al = (al * (period - 1) + losses[j]) / period
        out[j + 1] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def _atr_adx(h, l, c, p=14):
    """Wilder ATR, ADX, +DI, -DI."""
    n = len(c)
    atr = [None] * n
    adx = [None] * n
    pdi = [None] * n
    mdi = [None] * n
    if n <= 2 * p:
        return atr, adx, pdi, mdi
    tr = [0.0] * n
    pdm = [0.0] * n
    mdm = [0.0] * n
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        up, dn = h[i] - h[i - 1], l[i - 1] - l[i]
        pdm[i] = up if (up > dn and up > 0) else 0.0
        mdm[i] = dn if (dn > up and dn > 0) else 0.0
    s_tr, s_p, s_m = sum(tr[1:p + 1]), sum(pdm[1:p + 1]), sum(mdm[1:p + 1])
    dx = [None] * n
    for i in range(p, n):
        if i > p:
            s_tr = s_tr - s_tr / p + tr[i]
            s_p = s_p - s_p / p + pdm[i]
            s_m = s_m - s_m / p + mdm[i]
        atr[i] = s_tr / p
        pi = 100 * s_p / s_tr if s_tr > 0 else 0.0
        mi = 100 * s_m / s_tr if s_tr > 0 else 0.0
        pdi[i], mdi[i] = pi, mi
        den = pi + mi
        dx[i] = 100 * abs(pi - mi) / den if den > 0 else 0.0
    first = 2 * p - 1
    adx[first] = sum(dx[p:2 * p]) / p
    for i in range(first + 1, n):
        adx[i] = (adx[i - 1] * (p - 1) + dx[i]) / p
    return atr, adx, pdi, mdi


def _percentile(sorted_hist, value):
    """Anteil frueherer Werte, die kleiner sind als value (0..1)."""
    if len(sorted_hist) < PCT_MIN_HISTORY:
        return None
    return bisect_left(sorted_hist, value) / len(sorted_hist)


def _r(x, d=4):
    return None if x is None else round(float(x), d)


def session_of(ts):
    """Handelssession zu einem Zeitpunkt (UTC-Sekunden). Eine Achse, die
    DST-sicher aus New York und Zuerich abgeleitet wird."""
    et = datetime.fromtimestamp(int(ts), timezone.utc).astimezone(NY)
    zh = datetime.fromtimestamp(int(ts), timezone.utc).astimezone(ZH)
    m = et.hour * 60 + et.minute
    if 570 <= m < 630:
        return 'USA_OPEN'          # 09:30-10:30 New York
    if 630 <= m < 960:
        return 'USA'               # bis 16:00 New York
    if 960 <= m < 1080:
        return 'USA_NACHBOERSE'    # 16:00-18:00 New York
    if m >= 1080 or zh.hour < 8:
        return 'ASIEN'             # Abend/Nacht
    return 'EUROPA'                # Zuerich ab 08:00 bis US-Open


def hour_zh(ts):
    return datetime.fromtimestamp(int(ts), timezone.utc).astimezone(ZH).hour


def weekday_zh(ts):
    return datetime.fromtimestamp(int(ts), timezone.utc).astimezone(ZH).weekday()


def compute_series(bars):
    """Kennzahlen je 5M-Kerze. bars: aufsteigend sortiert, Dicts mit
    time/open/high/low/close/volume. Rueckgabe: Liste (gleiche Laenge),
    Eintrag None solange die Aufwaermphase laeuft."""
    n = len(bars)
    out = [None] * n
    if n <= WARMUP:
        return out
    o = [float(b['open']) for b in bars]
    h = [float(b['high']) for b in bars]
    l = [float(b['low']) for b in bars]
    c = [float(b['close']) for b in bars]
    v = [float(b.get('volume') or 0) for b in bars]
    atr, adx, pdi, mdi = _atr_adx(h, l, c)
    ema20, ema50 = _ema(c, 20), _ema(c, 50)
    rsi = _rsi(c)

    atr_hist, bbw_hist = [], []
    day_key = None
    cum_pv = cum_v = 0.0
    day_hl = {}
    prev_key = None
    for i in range(n):
        t = int(bars[i]['time'])
        et = datetime.fromtimestamp(t, timezone.utc).astimezone(NY)
        key = (et + timedelta(hours=6)).date().isoformat()   # CME-Tag: 18:00 NY -> naechster Tag
        if key != day_key:
            prev_key = day_key
            day_key = key
            cum_pv = cum_v = 0.0
            day_hl[key] = [h[i], l[i]]
        else:
            day_hl[key][0] = max(day_hl[key][0], h[i])
            day_hl[key][1] = min(day_hl[key][1], l[i])
        typical = (h[i] + l[i] + c[i]) / 3
        cum_pv += typical * v[i]
        cum_v += v[i]

        # Bollinger(20,2)
        bbw = pctb = None
        if i >= 19:
            win = c[i - 19:i + 1]
            mean = sum(win) / 20
            sd = math.sqrt(sum((x - mean) ** 2 for x in win) / 20)
            if mean:
                bbw = 4 * sd / mean
            pctb = (c[i] - (mean - 2 * sd)) / (4 * sd) if sd > 0 else 0.5

        a = atr[i]
        atr_pct = bbw_pct = None
        if a is not None:
            atr_pct = _percentile(atr_hist, a)
            insort(atr_hist, a)
        if bbw is not None:
            bbw_pct = _percentile(bbw_hist, bbw)
            insort(bbw_hist, bbw)

        if i < WARMUP or a is None or adx[i] is None or ema50[i] is None or a <= 0:
            continue

        vwap = cum_pv / cum_v if cum_v > 0 else None
        pdh = pdl = None
        if prev_key is not None and prev_key in day_hl:
            pdh, pdl = day_hl[prev_key]
        net12 = abs(c[i] - c[i - 12])
        path12 = sum(abs(c[j] - c[j - 1]) for j in range(i - 11, i + 1))
        close_ts = t + STEP
        et_close = datetime.fromtimestamp(close_ts, timezone.utc).astimezone(NY)
        mins = et_close.hour * 60 + et_close.minute - 570
        out[i] = {
            'time': t, 'close': _r(c[i], 4),
            'atr': _r(a), 'atr_pct': _r(atr_pct), 'adx': _r(adx[i], 2),
            'plus_di': _r(pdi[i], 2), 'minus_di': _r(mdi[i], 2),
            'ema20': _r(ema20[i]), 'ema50': _r(ema50[i]),
            'ema_gap_atr': _r((ema20[i] - ema50[i]) / a, 3),
            'ret60': _r(c[i] / c[i - 12] - 1, 5), 'ret240': _r(c[i] / c[i - 48] - 1, 5) if i >= 48 else None,
            'ret240_atr': _r((c[i] - c[i - 48]) / a, 3) if i >= 48 else None,
            'er60': _r(net12 / path12, 3) if path12 > 0 else None,
            'rsi': _r(rsi[i], 2), 'bb_width': _r(bbw, 5), 'bb_width_pct': _r(bbw_pct),
            'bb_pctb': _r(pctb, 3),
            'dist_vwap_atr': _r((c[i] - vwap) / a, 3) if vwap else None,
            'dist_pdh_atr': _r((c[i] - pdh) / a, 3) if pdh else None,
            'dist_pdl_atr': _r((c[i] - pdl) / a, 3) if pdl else None,
            'ny_min_since_open': mins if 0 <= mins < 390 else None,
            'last_body_atr': _r(abs(c[i] - o[i]) / a, 3),
        }
    return out


def classify(f, news_day=False):
    """Features -> Marktlage. Regeln bewusst einfach und erklaerbar."""
    if not f:
        return {'regime': 'UNBEKANNT', 'vol': 'UNBEKANNT', 'trend_dir': 0, 'arrow': '?', 'news_day': bool(news_day)}
    up = f['ema20'] > f['ema50'] and f['close'] > f['ema50'] and (f.get('ret240') or 0) > 0
    dn = f['ema20'] < f['ema50'] and f['close'] < f['ema50'] and (f.get('ret240') or 0) < 0
    td = 1 if up else -1 if dn else 0
    adx, ap = f['adx'], f.get('atr_pct')
    if adx >= 25 and td != 0:
        regime = 'TREND_HOCH' if td > 0 else 'TREND_RUNTER'
    elif adx < 20:
        regime = 'CHOP' if (ap is not None and ap >= 0.75) else 'RANGE'
    else:
        regime = 'UEBERGANG'
    vol = 'UNBEKANNT' if ap is None else 'RUHIG' if ap < 0.25 else 'HEKTISCH' if ap > 0.75 else 'NORMAL'
    arrow = ARROWS.get(regime) or ('↗' if td > 0 else '↘' if td < 0 else '→')
    return {'regime': regime, 'vol': vol, 'trend_dir': td, 'arrow': arrow, 'news_day': bool(news_day)}


def side_vs_trend(side, trend_dir):
    if not trend_dir or side not in ('LONG', 'SHORT'):
        return 'NEUTRAL'
    return 'MIT_TREND' if (side == 'LONG') == (trend_dir > 0) else 'GEGEN_TREND'


def features_at(times, series, cutoff_ts):
    """Letzte vollstaendig abgeschlossene 5M-Kerze bis cutoff_ts (UTC-Sek.).
    times: Liste der Kerzen-Startzeiten (aufsteigend)."""
    idx = bisect_right(times, int(cutoff_ts) - STEP) - 1
    if idx < 0:
        return None
    return series[idx]
