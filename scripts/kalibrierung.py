"""Kalibrierung Risk Aktien.

Lernt pro Variante (Fenster × Normierung × Glättung) die Gewichte per logistischer Regression
auf historischen Swing-Hochs (1) und -Tiefs (0) bis Ende 2018, baut die Perzentil-Tabelle aus
allen Trainingstagen und prüft auf 2019–heute. Vergleich: Risk v2 (Krypto) unverändert.

Aufruf: python scripts/kalibrierung.py   →  modell/varianten.json, berichte/kalibrierung.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).parent))
from risk_aktien_kern import bereinige, ema, interp_q, merkmale, skala  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TRAIN_ENDE = pd.Timestamp("2018-12-31")
TEST_START = pd.Timestamp("2019-01-01")
START = pd.Timestamp("1995-01-01")
PIVOT_L = 40          # Hoch/Tief über ±40 Handelstage
PIVOT_H = 120         # Folgebewegung innert 120 Handelstagen
NACHBAR = 3           # ±3 Tage um den Pivot zählen mit

# Risk v2 (Krypto), eingefroren, aus risk_v2.pine
V2 = dict(fenster=[20, 50, 140, 350], norm="roh", ema=5, c0=-0.009602,
          w=[3.048234, 9.195904, -1.311095, 0.174051],
          q=[-9.95068, -5.41719, -4.59295, -4.03028, -3.63381, -3.30518, -3.03685, -2.84592, -2.66794, -2.48203,
             -2.30145, -2.18585, -2.04304, -1.93627, -1.83148, -1.74348, -1.64743, -1.56541, -1.49524, -1.41219,
             -1.34268, -1.28179, -1.21335, -1.15505, -1.10147, -1.04168, -0.98952, -0.93388, -0.87613, -0.82381,
             -0.77325, -0.71683, -0.66687, -0.60959, -0.55793, -0.50786, -0.45836, -0.41426, -0.37485, -0.33521,
             -0.29144, -0.24489, -0.20392, -0.16672, -0.12990, -0.08520, -0.05432, -0.01108, 0.02797, 0.06518,
             0.11074, 0.14399, 0.18401, 0.22431, 0.26602, 0.29843, 0.34355, 0.37836, 0.42135, 0.46963,
             0.51000, 0.55627, 0.59933, 0.65121, 0.69801, 0.75883, 0.81168, 0.87499, 0.93664, 0.99035,
             1.05759, 1.12138, 1.19033, 1.24867, 1.33560, 1.40453, 1.47454, 1.54581, 1.62730, 1.71742,
             1.80407, 1.89493, 1.98022, 2.08624, 2.19596, 2.31286, 2.43067, 2.56160, 2.66834, 2.81171,
             2.97691, 3.16383, 3.34918, 3.57439, 3.85528, 4.21606, 4.79896, 5.48132, 6.41893, 8.52398,
             20.65047])

VARIANTEN = {}
for fname, fen in {"A": (14, 35, 100, 250), "B": (20, 50, 100, 200), "C": (20, 50, 140, 350)}.items():
    for norm in ("roh", "vol"):
        for e in (5, 10):
            VARIANTEN[f"{fname}-{norm}-ema{e}"] = dict(fenster=list(fen), norm=norm, ema=e)


def lade_kurse() -> dict[str, pd.Series]:
    k = pd.read_parquet(ROOT / "daten" / "kurse.parquet")
    cfg = pd.read_csv(ROOT / "config" / "yuh_aktien.csv", sep=";", dtype=str)
    out = {}
    for t in cfg["ticker"]:
        if t in k.columns:
            s = bereinige(k[t])
            s = s[s.index >= START]
            if len(s) >= 600 and (k.index[-1] - s.index[-1]).days <= 10:
                out[t] = s
    return out


def pivots(s: pd.Series) -> pd.Series:
    """1 = Swing-Hoch mit anschliessendem Rückgang, 0 = Swing-Tief mit anschliessendem Anstieg, sonst NaN."""
    p = s.values
    n = len(p)
    sig = np.log(s).diff().rolling(250, min_periods=120).std().values
    roll_max = s.rolling(2 * PIVOT_L + 1, center=True, min_periods=PIVOT_L + 1).max().values
    roll_min = s.rolling(2 * PIVOT_L + 1, center=True, min_periods=PIVOT_L + 1).min().values
    lab = np.full(n, np.nan)
    for i in range(PIVOT_L, n - PIVOT_L):
        if np.isnan(sig[i]):
            continue
        thr = max(0.10, 2.0 * sig[i] * np.sqrt(60))
        fut = p[i + 1:min(n, i + 1 + PIVOT_H)]
        if p[i] == roll_max[i] and fut.min() / p[i] - 1 <= -thr:
            lab[max(0, i - NACHBAR):i + NACHBAR + 1] = 1
        elif p[i] == roll_min[i] and fut.max() / p[i] - 1 >= thr:
            lab[max(0, i - NACHBAR):i + NACHBAR + 1] = 0
    return pd.Series(lab, index=s.index)


def fit(kurse, labels, var):
    Xs, ys, raws = [], [], []
    for t, s in kurse.items():
        X = merkmale(s, tuple(var["fenster"]), var["norm"])
        m = (X.index <= TRAIN_ENDE) & X.notna().all(axis=1).values
        lab = labels[t]
        ml = m & lab.notna().values
        if ml.any():
            Xs.append(X.values[ml])
            ys.append(lab.values[ml])
    X = np.vstack(Xs)
    y = np.concatenate(ys)
    lr = LogisticRegression(C=1.0, max_iter=2000).fit(X, y)
    w, c0 = lr.coef_[0].tolist(), float(lr.intercept_[0])
    for t, s in kurse.items():
        X = merkmale(s, tuple(var["fenster"]), var["norm"])
        m = (X.index <= TRAIN_ENDE) & X.notna().all(axis=1).values
        if m.any():
            raws.append(c0 + X.values[m] @ np.array(w))
    q = np.percentile(np.concatenate(raws), np.linspace(0, 100, 101)).tolist()
    return dict(var, w=w, c0=c0, q=q, n_train=int(len(y)), n_top=int(y.sum()))


def risk(s, mod):
    X = merkmale(s, tuple(mod["fenster"]), mod["norm"])
    raw = mod["c0"] + X.values @ np.array(mod["w"])
    p = interp_q(raw, np.array(mod["q"]))
    p[np.isnan(raw)] = np.nan
    return pd.Series(skala(ema(p, mod["ema"])), index=s.index)


def eintritte(r: np.ndarray, lvl: float, oben: bool, pause: int = 20) -> list[int]:
    ev, letzte = [], -10**9
    for i in range(1, len(r)):
        a, b = r[i - 1], r[i]
        if np.isnan(a) or np.isnan(b):
            continue
        hit = (a < lvl <= b) if oben else (a >= lvl > b)
        if hit and i - letzte > pause:
            ev.append(i)
            letzte = i
    return ev


def auswerten(kurse, labels, mod, voltert):
    tage = []      # (risk, tercile)
    ev = {"80": [], "90": [], "20": []}
    alle_fwd, alle_dd, alle_up = [], [], []
    y_true, y_score = [], []
    for t, s in kurse.items():
        r = risk(s, mod).values
        p = s.values
        idx = s.index
        test = idx >= TEST_START
        n = len(p)
        for i in np.where(test & ~np.isnan(r))[0]:
            tage.append((r[i], voltert[t]))
        lab = labels[t].values
        mt = test & ~np.isnan(lab) & ~np.isnan(r)
        y_true += lab[mt].tolist()
        y_score += r[mt].tolist()

        def fwd(i, h):
            if i + h >= n:
                return None
            seg = p[i + 1:i + h + 1]
            return p[i + h] / p[i] - 1, seg.min() / p[i] - 1, seg.max() / p[i] - 1
        ti = np.where(test)[0]
        for i in ti[::5]:
            f = fwd(i, 60)
            if f:
                alle_fwd.append(f[0]); alle_dd.append(f[1]); alle_up.append(f[2])
        for key, lvl, oben in (("80", 80, True), ("90", 90, True), ("20", 20, False)):
            for i in eintritte(r, lvl, oben):
                if idx[i] < TEST_START:
                    continue
                f60, f90 = fwd(i, 60), fwd(i, 90)
                if f60 and f90:
                    ev[key].append((f60[0], f60[1], f60[2], f90[1], f90[2], voltert[t]))
    tage = np.array(tage)
    res = {}
    for name, sel in (("alle", slice(None)),):
        rr = tage[:, 0]
        res["anteil80"] = float((rr >= 80).mean() * 100)
        res["anteil90"] = float((rr >= 90).mean() * 100)
        res["anteil20"] = float((rr < 20).mean() * 100)
    for v in (0, 1, 2):
        rr = tage[tage[:, 1] == v, 0]
        res[f"a80_v{v}"] = float((rr >= 80).mean() * 100)
        res[f"a20_v{v}"] = float((rr < 20).mean() * 100)
    res["auc"] = float(roc_auc_score(y_true, y_score))
    res["basis_fwd60"] = float(np.median(alle_fwd) * 100)
    res["basis_dd15"] = float((np.array(alle_dd) <= -0.15).mean() * 100)
    res["basis_up15"] = float((np.array(alle_up) >= 0.15).mean() * 100)
    for key in ev:
        a = np.array(ev[key]) if ev[key] else np.zeros((0, 6))
        res[f"n{key}"] = int(len(a))
        if len(a):
            res[f"fwd60_{key}"] = float(np.median(a[:, 0]) * 100)
            res[f"dd15_{key}"] = float((a[:, 1] <= -0.15).mean() * 100)
            res[f"dd20_90_{key}"] = float((a[:, 3] <= -0.20).mean() * 100)
            res[f"up15_{key}"] = float((a[:, 2] >= 0.15).mean() * 100)
    return res


def main():
    kurse = lade_kurse()
    print(f"{len(kurse)} Titel mit genug Historie")
    labels = {t: pivots(s) for t, s in kurse.items()}
    med_sig = pd.Series({t: np.log(s).diff().std() for t, s in kurse.items()})
    voltert = pd.qcut(med_sig, 3, labels=False).to_dict()
    ergebnisse, modelle = {}, {}
    ergebnisse["Risk v2 (Krypto, unverändert)"] = auswerten(kurse, labels, V2, voltert)
    for name, var in VARIANTEN.items():
        mod = fit(kurse, labels, var)
        modelle[name] = mod
        ergebnisse[name] = auswerten(kurse, labels, mod, voltert)
        print(name, {k: round(v, 2) for k, v in ergebnisse[name].items() if k in ("auc", "anteil80", "dd15_80", "fwd60_20")})
    (ROOT / "modell").mkdir(exist_ok=True)
    (ROOT / "modell" / "varianten.json").write_text(json.dumps(modelle, indent=1))
    df = pd.DataFrame(ergebnisse).T
    df.to_csv(ROOT / "berichte" / "kalibrierung_tabelle.csv", sep=";", float_format="%.2f")
    print(df.round(1).to_string())
    return kurse, labels, modelle, df


if __name__ == "__main__":
    main()
