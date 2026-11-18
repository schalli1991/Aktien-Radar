"""Portfolio-Test: Momentum-Puffer allein vs. Momentum mit Aufmerksamkeits-Filter (Wikipedia, 90 Tage ggü. Vorjahr)."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, pandas as pd, regeltest as RT
ROOT = Path(__file__).resolve().parents[1]
kurse, P, I = RT.panel()
A = pd.read_parquet(ROOT / "daten" / "aufmerksamkeit.parquet"); A.index = pd.to_datetime(A.index)
z = pd.read_csv(ROOT / "config" / "wikipedia.csv", sep=";", dtype=str).fillna("")
schlecht = set(z[z.fix != ""]["ticker"])
cols = [c for c in P.columns if c in A.columns and c not in schlecht and A[c].notna().sum() > 1500]
P = P[cols]; A = A[cols].reindex(pd.date_range(A.index.min(), A.index.max())).astype(float)
a90 = A.rolling(90, min_periods=70).mean(); trend = (a90 / a90.shift(365)).reindex(P.index, method="ffill")
ret = P.pct_change(fill_method=None).fillna(0)
mom = P.shift(21) / P.shift(252) - 1
rb = [d for d in P.resample("BME").last().index if d in P.index and d >= pd.Timestamp("2016-08-01")]
def sim(waehle, fee=0.015):
    W = pd.DataFrame(0.0, index=P.index, columns=cols); held = []
    rbs = set(rb); cur = pd.Series(0.0, index=cols)
    for d in P.index:
        if d in rbs:
            held = waehle(d, held)
            cur = pd.Series(0.0, index=cols)
            if held: cur[held] = 1 / len(held)
        W.loc[d] = cur
    turn = W.diff().abs().sum(axis=1).fillna(0)
    return (W.shift(1) * ret).sum(axis=1) - turn.shift(1).fillna(0) * fee, turn
def puffer(d, held, top=20, keep=40):
    m = mom.loc[d].dropna(); rk = m.rank(ascending=False)
    h = [t for t in held if t in rk.index and rk[t] <= keep]
    for t in m.nlargest(top).index:
        if len(h) >= top: break
        if t not in h: h.append(t)
    return h
def mit_att(d, held, top=20, pool=40, keep=60, schwelle=1.5):
    m = mom.loc[d].dropna(); rk = m.rank(ascending=False); tr = trend.loc[d]
    h = [t for t in held if t in rk.index and rk[t] <= keep]
    kand = [t for t in m.nlargest(pool).index if t not in h and tr.get(t, np.nan) >= schwelle]
    kand.sort(key=lambda t: -tr[t])
    for t in kand:
        if len(h) >= top: break
        h.append(t)
    return h
def nur_att(d, held, top=20):
    tr = trend.loc[d].dropna(); tr = tr[mom.loc[d].reindex(tr.index).notna()]
    return list(tr.nlargest(top).index)
ew = ret.where(mom.notna()).mean(axis=1)
def st(r, a, b):
    m = (r.index >= a) & (r.index <= b); c1, c2 = RT.kennzahlen(r[m]), RT.kennzahlen(ew[m])
    yr = pd.DataFrame({'s': r[m], 'e': ew[m]}).groupby(r[m].index.year).apply(lambda x: (1 + x).prod() - 1)
    return f"{c1[0]:5.1f} % p.a. (EW {c2[0]:5.1f} %) | MDD {c1[1]:6.1f} % | Jahre besser als EW {(yr.s > yr.e).sum()}/{len(yr)}"
base, tb = sim(puffer)
res = {"Momentum-Puffer (heutige Regel)": (base, tb),
       "Momentum Top 40 + Aufmerksamkeit ≥ 1.5": sim(mit_att),
       "Momentum Top 40 + Aufmerksamkeit ≥ 1.2": sim(lambda d, h: mit_att(d, h, schwelle=1.2)),
       "Momentum Top 60 + Aufmerksamkeit ≥ 1.5": sim(lambda d, h: mit_att(d, h, pool=60, keep=80)),
       "Nur Aufmerksamkeit (Top 20 Trend)": sim(nur_att)}
print(f"{len(cols)} Titel, ab {rb[0].date()}")
for k, (r, t) in res.items():
    yrs = pd.DataFrame({'s': r, 'b': base}).loc['2016-09':].groupby(r.loc['2016-09':].index.year).apply(lambda x: (1 + x).prod() - 1)
    print(f"{k:42s} 2016–2020: {st(r, '2016-09-01', '2020-12-31')}")
    print(f"{'':42s} 2021–2026: {st(r, '2021-01-01', '2026-11-18')} | Umschlag/J {t['2021':].sum() / 5.9:.1f} | Jahre besser als Momentum allein {(yrs.s > yrs.b).sum()}/{len(yrs)}")
