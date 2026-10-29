"""API-Routen der TAURUS Analyse (Seiten 1-4 unter /analyse)."""
import logging
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

import analysis

router = APIRouter()
_CACHE = {}
TTL = 30


def _cached(key, fn):
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    value = fn()
    _CACHE[key] = (time.time(), value)
    return value


@router.get('/analyse')
def analyse_page():
    return FileResponse('static/analyse.html')


@router.get('/api/analysis/market')
def analysis_market(min_n: int = 10):
    if not 3 <= min_n <= 100:
        raise HTTPException(400, 'min_n muss zwischen 3 und 100 liegen')
    try:
        return _cached(('market', min_n), lambda: analysis.market_overview(min_n))
    except Exception as exc:
        logging.exception('Analysis market failed')
        raise HTTPException(503, 'Marktlage nicht verfügbar') from exc


@router.get('/api/analysis/report')
def analysis_report(dim: str = 'regime', market: str = 'all', min_n: int = 10):
    from paper_engine import MARKETS
    if dim not in analysis.DIMS:
        raise HTTPException(400, 'Unbekannte Dimension')
    if market != 'all' and market not in MARKETS:
        raise HTTPException(400, 'Unbekannter Markt')
    if not 3 <= min_n <= 100:
        raise HTTPException(400, 'min_n muss zwischen 3 und 100 liegen')
    try:
        return _cached(('report', dim, market, min_n),
                       lambda: analysis.report(dim, None if market == 'all' else market, min_n))
    except Exception as exc:
        logging.exception('Analysis report failed')
        raise HTTPException(503, 'Auswertung nicht verfügbar') from exc


@router.get('/api/analysis/chart')
def analysis_chart(market: str = 'nq', bars: int = 576):
    from paper_engine import MARKETS
    if market not in MARKETS:
        raise HTTPException(400, 'Unbekannter Markt')
    if not 50 <= bars <= 2000:
        raise HTTPException(400, 'bars muss zwischen 50 und 2000 liegen')
    try:
        return _cached(('chart', market, bars), lambda: analysis.chart_data(market, bars))
    except Exception as exc:
        logging.exception('Analysis chart failed')
        raise HTTPException(503, 'Chart nicht verfügbar') from exc
