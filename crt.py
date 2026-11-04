"""CRT – Candle Range Theory (Test), objektiv definiert aus 5M-Kerzen.

Ablauf wie im Lehrvideo (4H-Spanne, Einstieg auf 15M):
  1. Spanne = Hoch/Tief der zuletzt ABGESCHLOSSENEN 4H-Kerze
     (4H-Bloecke nach CME-Tag: 18, 22, 02, 06, 10, 14 Uhr New York).
  2. Sweep: eine abgeschlossene 15M-Kerze der laufenden 4H-Kerze faellt unter das
     Tief der Spanne (Long-Fall) bzw. steigt ueber das Hoch (Short-Fall).
  3. Zurueckholen: dieselbe (Docht-Sweep) oder eine spaetere 15M-Kerze derselben
     4H-Kerze schliesst wieder innerhalb der Spanne (nicht die erste 15M-Kerze).
  4. Einstieg, zwei Varianten:
       reclaim  sofort beim Schluss der zurueckholenden 15M-Kerze
       retest   erst beim Ruecklauf in den "Mitigation Block" = Koerper der letzten
                15M-Gegenkerze vor der Umkehr; Signal, wenn eine 5M-Kerze in den Block
                laeuft und ueber (unter) ihm schliesst. Verfaellt mit der 4H-Kerze.
  5. Stop: hinter dem Sweep-Extrem + 0.1 ATR(5M). Ziel, zwei Varianten:
       mid   Mitte der 4H-Spanne
       full  anderes Ende der 4H-Spanne ("CRT High")
Hoechstens ein Setup je Richtung und 4H-Kerze. Nur abgeschlossene Kerzen.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from strategies import tile, signal_with_params

NY = ZoneInfo('America/New_York')
KEYS = ('crt_reclaim_mid', 'crt_reclaim_full', 'crt_retest_mid', 'crt_retest_full')
NAMES = {
    'crt_reclaim_mid': 'CRT: Zurückholen, Ziel Mitte',
    'crt_reclaim_full': 'CRT: Zurückholen, Ziel 4H-Ende',
    'crt_retest_mid': 'CRT: Mitigation-Retest, Ziel Mitte',
    'crt_retest_full': 'CRT: Mitigation-Retest, Ziel 4H-Ende',
}


def block_key(ts):
    """4H-Block nach CME-Handelstag (Start 18:00 New York)."""
    t = datetime.fromtimestamp(int(ts), timezone.utc).astimezone(NY) + timedelta(hours=6)
    return (t.date().isoformat(), t.hour // 4)


def _atr(bars, n=14):
    out, tr_avg = [None] * len(bars), None
    for i in range(1, len(bars)):
        b, p = bars[i], bars[i - 1]
        tr = max(b['high'] - b['low'], abs(b['high'] - p['close']), abs(b['low'] - p['close']))
        tr_avg = tr if tr_avg is None else tr_avg + (tr - tr_avg) / n
        if i >= n:
            out[i] = tr_avg
    return out


class _Side:
    """Zustand einer Richtung innerhalb einer 4H-Kerze."""
    def __init__(self):
        self.swept = False
        self.extreme = None
        self.reclaimed = False
        self.zone = None          # (unten, oben) Mitigation Block
        self.retest_done = False


def build(bars, market='nq'):
    found = {k: [] for k in KEYS}
    if len(bars) < 120:
        return [tile(k, NAMES[k], 'neutral', 'Mindestens 120 abgeschlossene 5M-Kerzen benötigt', [], []) for k in KEYS]
    atr = _atr(bars)
    cur_key, cur = None, None            # laufende 4H-Kerze: [hoch, tief]
    rng = None                           # (hoch, tief) der letzten abgeschlossenen 4H-Kerze
    q15, q_list = None, []               # laufende 15M-Kerze, abgeschlossene 15M-Kerzen des Blocks
    L = S = None

    def sig(key, side, b, entry, stop, tp, reason):
        if (side == 'LONG' and stop < entry < tp) or (side == 'SHORT' and tp < entry < stop):
            found[key].append(signal_with_params(key, side, b['time'], entry, stop, tp, reason, timeframe='5m'))

    for i, b in enumerate(bars):
        k = block_key(b['time'])
        if k != cur_key:
            if cur is not None:
                rng = tuple(cur)
            cur_key, cur = k, [b['high'], b['low']]
            q15, q_list = None, []
            L, S = _Side(), _Side()
        else:
            cur[0] = max(cur[0], b['high']); cur[1] = min(cur[1], b['low'])
        a = atr[i]
        if rng is None or a is None:
            continue
        hi, lo = rng
        mid = (hi + lo) / 2
        buf = 0.1 * a

        # --- Retest des Mitigation Blocks auf 5M (vor dem 15M-Update, nur fruehere Information)
        if L.zone and not L.retest_done:
            z_lo, z_hi = L.zone
            if b['close'] < L.extreme or b['high'] >= hi:
                L.retest_done = True            # Setup ungueltig oder Ziel ohne Ruecklauf erreicht
            elif b['low'] <= z_hi and b['close'] > z_lo and b['close'] > b['open']:
                L.retest_done = True
                stop = L.extreme - buf
                sig('crt_retest_mid', 'LONG', b, b['close'], stop, mid, 'CRT: Sweep unter 4H-Tief, Retest Mitigation Block; Ziel Mitte')
                sig('crt_retest_full', 'LONG', b, b['close'], stop, hi, 'CRT: Sweep unter 4H-Tief, Retest Mitigation Block; Ziel 4H-Hoch')
        if S.zone and not S.retest_done:
            z_lo, z_hi = S.zone
            if b['close'] > S.extreme or b['low'] <= lo:
                S.retest_done = True
            elif b['high'] >= z_lo and b['close'] < z_hi and b['close'] < b['open']:
                S.retest_done = True
                stop = S.extreme + buf
                sig('crt_retest_mid', 'SHORT', b, b['close'], stop, mid, 'CRT: Sweep über 4H-Hoch, Retest Mitigation Block; Ziel Mitte')
                sig('crt_retest_full', 'SHORT', b, b['close'], stop, lo, 'CRT: Sweep über 4H-Hoch, Retest Mitigation Block; Ziel 4H-Tief')

        # --- 15M-Kerze fortschreiben; abgeschlossen mit der 5M-Kerze ab Minute :10/:25/:40/:55
        start = b['time'] // 900 * 900
        if q15 is None or q15['time'] != start:
            q15 = {'time': start, 'open': b['open'], 'high': b['high'], 'low': b['low'], 'close': b['close']}
        else:
            q15.update(high=max(q15['high'], b['high']), low=min(q15['low'], b['low']), close=b['close'])
        if (b['time'] - start) != 600:
            continue
        q = dict(q15)
        q_list.append(q)

        # Long: Sweep unter das 4H-Tief, dann Schluss zurueck darueber
        if not L.reclaimed:
            if q['low'] < lo:
                L.swept = True
                L.extreme = q['low'] if L.extreme is None else min(L.extreme, q['low'])
            if L.swept and q['close'] > lo and len(q_list) >= 2:
                L.reclaimed = True
                stop = L.extreme - buf
                sig('crt_reclaim_mid', 'LONG', b, q['close'], stop, mid, 'CRT: Sweep unter 4H-Tief, 15M zurück; Ziel Mitte')
                sig('crt_reclaim_full', 'LONG', b, q['close'], stop, hi, 'CRT: Sweep unter 4H-Tief, 15M zurück; Ziel 4H-Hoch')
                bear = [x for x in q_list[:-1] if x['close'] < x['open']]
                if bear:
                    z = bear[-1]
                    if z['open'] < q['close']:
                        L.zone = (z['close'], z['open'])
        # Short: Sweep ueber das 4H-Hoch, dann Schluss zurueck darunter
        if not S.reclaimed:
            if q['high'] > hi:
                S.swept = True
                S.extreme = q['high'] if S.extreme is None else max(S.extreme, q['high'])
            if S.swept and q['close'] < hi and len(q_list) >= 2:
                S.reclaimed = True
                stop = S.extreme + buf
                sig('crt_reclaim_mid', 'SHORT', b, q['close'], stop, mid, 'CRT: Sweep über 4H-Hoch, 15M zurück; Ziel Mitte')
                sig('crt_reclaim_full', 'SHORT', b, q['close'], stop, lo, 'CRT: Sweep über 4H-Hoch, 15M zurück; Ziel 4H-Tief')
                bull = [x for x in q_list[:-1] if x['close'] > x['open']]
                if bull:
                    z = bull[-1]
                    if z['open'] > q['close']:
                        S.zone = (z['open'], z['close'])

    cur_t = bars[-1]['time']
    return [tile(k, NAMES[k], 'green' if found[k] and found[k][-1]['time'] == cur_t else 'neutral',
                 '4H-Spanne, 15M-Sweep und Zurückholen', found[k],
                 [('Signal letzte Kerze', 'green' if found[k] and found[k][-1]['time'] == cur_t else 'neutral')])
            for k in KEYS]
