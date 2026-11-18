"""Gemeinsame Rechenbausteine für Risk Aktien (Kalibrierung und Tagesberechnung)."""
from __future__ import annotations

import numpy as np
import pandas as pd

# Skala wie Risk v2: Perzentil-Knoten 0/5/50/90/95/100 → Anzeige 0/20/50/80/90/100
KN_P = np.array([0, 5, 50, 90, 95, 100], dtype=float)
KN_D = np.array([0, 20, 50, 80, 90, 100], dtype=float)
VOL_FENSTER = 250


def bereinige(s: pd.Series) -> pd.Series:
    """Entfernt offensichtliche Fehlkurse: einzelne Tagesspitzen, die am Folgetag zurücklaufen."""
    s = s.dropna()
    s = s[s > 0].astype(float)
    if len(s) < 3:
        return s
    lr = np.log(s).diff()
    spitze = (lr.abs() > 0.4) & (lr.shift(-1).abs() > 0.3) & (np.sign(lr) != np.sign(lr.shift(-1)))
    if spitze.any():
        s = s.mask(spitze).ffill()
    return s


def merkmale(s: pd.Series, fenster: tuple[int, ...], norm: str) -> pd.DataFrame:
    lp = np.log(s)
    cols = {}
    for k in fenster:
        cols[f"d{k}"] = lp - np.log(s.rolling(k, min_periods=k).mean())
    X = pd.DataFrame(cols, index=s.index)
    if norm == "vol":
        sig = lp.diff().rolling(VOL_FENSTER, min_periods=120).std()
        X = X.div(sig, axis=0)
    return X


def interp_q(x: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Wert → Perzentil 0–100 anhand einer aufsteigenden Tabelle mit 101 Stützstellen."""
    return np.interp(x, q, np.linspace(0, 100, len(q)))


def ema(x: np.ndarray, n: int) -> np.ndarray:
    a = 2.0 / (n + 1.0)
    out = np.full_like(x, np.nan, dtype=float)
    e = np.nan
    for i, v in enumerate(x):
        if np.isnan(v):
            continue
        e = v if np.isnan(e) else a * v + (1 - a) * e
        out[i] = e
    return out


def skala(p: np.ndarray) -> np.ndarray:
    return np.interp(p, KN_P, KN_D)


def risk_serie(s: pd.Series, modell: dict) -> pd.Series:
    X = merkmale(s, tuple(modell["fenster"]), modell["norm"])
    raw = modell["c0"] + X.values @ np.array(modell["w"])
    p = np.where(np.isnan(raw), np.nan, interp_q(np.nan_to_num(raw), np.array(modell["q"])))
    return pd.Series(skala(ema(p, modell["ema"])), index=s.index)
