"""Test Themen-Momentum: monatlich die stärksten Themen (gleich gewichtete Körbe) halten."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, pandas as pd, regeltest as RT
ROOT = Path(__file__).resolve().parents[1]
kurse, P, I = RT.panel()
ret = P.pct_change(fill_method=None)
cfg = pd.read_csv(ROOT/"config"/"yuh_aktien.csv", sep=";", dtype=str).set_index("ticker")
thema = cfg["thema"].reindex(P.columns)
# Themenkorb-Tagesrendite (gleich gewichtet über vorhandene Titel)
T = pd.DataFrame({th: ret[cols].mean(axis=1) for th, cols in thema.groupby(thema).groups.items()})
Tn = pd.DataFrame({th: P[cols].notna().sum(axis=1) for th, cols in thema.groupby(thema).groups.items()})
T = T.where(Tn >= 3)
TI = (1 + T.fillna(0)).cumprod().where(T.notna())
rb = set(d for d in P.resample("BME").last().index if d in P.index)
def run(lb, skip, topk, fee=0.015, stock_top=None):
    mom_t = TI.shift(skip) / TI.shift(lb) - 1
    mom_s = P.shift(21) / P.shift(252) - 1
    W = np.zeros(P.shape); cur = np.zeros(P.shape[1]); cols = list(P.columns); ix = {c:i for i,c in enumerate(cols)}
    for k, d in enumerate(P.index):
        if d in rb:
            m = mom_t.loc[d].dropna()
            if len(m) >= topk + 3:
                best = m.nlargest(topk).index
                pool = [c for c in cols if thema[c] in best and pd.notna(P.at[d, c])]
                if stock_top:
                    ms = mom_s.loc[d, pool].dropna(); pool = list(ms.nlargest(stock_top).index)
                cur = np.zeros(len(cols))
                for c in pool: cur[ix[c]] = 1/len(pool)
        W[k] = cur
    W = pd.DataFrame(W, index=P.index, columns=cols)
    turn = W.diff().abs().sum(axis=1).fillna(0)
    r = (W.shift(1) * ret.fillna(0)).sum(axis=1) - turn.shift(1).fillna(0) * fee
    return r, turn
ew = ret.where((P.shift(252)).notna()).mean(axis=1)
def st(r, a, b):
    m = (r.index >= a) & (r.index <= b)
    c1, c2 = RT.kennzahlen(r[m]), RT.kennzahlen(ew[m])
    yr = pd.DataFrame({'s': r[m], 'e': ew[m]}).groupby(r[m].index.year).apply(lambda x: (1+x).prod()-1)
    return f"{c1[0]:5.1f} % vs EW {c2[0]:5.1f} % | MDD {c1[1]:6.1f} vs {c2[1]:6.1f} | Jahre besser {(yr.s>yr.e).sum()}/{len(yr)}"
for name, kw in {"Top 3 Themen, 6 Monate": dict(lb=126, skip=0, topk=3),
                 "Top 3 Themen, 12-1 Monate": dict(lb=252, skip=21, topk=3),
                 "Top 5 Themen, 6 Monate": dict(lb=126, skip=0, topk=5),
                 "Top 3 Themen, 3 Monate": dict(lb=63, skip=0, topk=3),
                 "Top 5 Themen 6M, darin Top 20 Aktien-Momentum": dict(lb=126, skip=0, topk=5, stock_top=20)}.items():
    r, turn = run(**kw)
    print(f"{name:46s} 2005–18: {st(r,'2005-01-01','2018-12-31')}")
    print(f"{'':46s} 2019–26: {st(r,'2019-01-01','2026-11-18')} | Umschlag/J {turn['2019':].sum()/8:.1f}")
print("--- ohne Gebühren (reines Signal) ---")
for name, kw in {"Top 3 Themen, 6 Monate": dict(lb=126, skip=0, topk=3, fee=0),
                 "Top 3 Themen, 12-1 Monate": dict(lb=252, skip=21, topk=3, fee=0),
                 "Top 5 Themen, 6 Monate": dict(lb=126, skip=0, topk=5, fee=0)}.items():
    r, turn = run(**kw)
    print(f"{name:46s} 2005–18: {st(r,'2005-01-01','2018-12-31')}")
    print(f"{'':46s} 2019–26: {st(r,'2019-01-01','2026-11-18')}")
print("--- günstig umsetzbar: Top-Themen mit Puffer, je Thema die 5 stärksten Aktien, 1.5 % Gebühr ---")
def run_buf(lb=126, skip=0, enter=3, keep=6, per=5, freq="BME", fee=0.015, s_keep=10):
    mom_t = TI.shift(skip) / TI.shift(lb) - 1
    mom_s = P.shift(21) / P.shift(252) - 1
    rbs = set(d for d in P.resample(freq).last().index if d in P.index)
    cols = list(P.columns); ix = {c:i for i,c in enumerate(cols)}
    W = np.zeros(P.shape); cur = np.zeros(len(cols)); held_t = []; held_s = {}
    for k, d in enumerate(P.index):
        if d in rbs:
            m = mom_t.loc[d].dropna()
            if len(m) >= keep:
                rk = m.rank(ascending=False)
                held_t = [t for t in held_t if t in rk.index and rk[t] <= keep]
                for t in m.nlargest(enter).index:
                    if len(held_t) >= enter: break
                    if t not in held_t: held_t.append(t)
                ms = mom_s.loc[d].dropna()
                new = {}
                for t in held_t:
                    pool = ms[[c for c in ms.index if thema[c] == t]]
                    r2 = pool.rank(ascending=False)
                    keepers = [c for c in held_s.get(t, []) if c in r2.index and r2[c] <= s_keep]
                    for c in pool.nlargest(per).index:
                        if len(keepers) >= per: break
                        if c not in keepers: keepers.append(c)
                    new[t] = keepers
                held_s = new
                allc = [c for v in held_s.values() for c in v]
                cur = np.zeros(len(cols))
                for c in allc: cur[ix[c]] = 1/len(allc)
        W[k] = cur
    W = pd.DataFrame(W, index=P.index, columns=cols)
    turn = W.diff().abs().sum(axis=1).fillna(0)
    r = (W.shift(1) * ret.fillna(0)).sum(axis=1) - turn.shift(1).fillna(0) * fee
    return r, turn
for name, kw in {"3 Themen (Puffer 6), je 5 Aktien, monatlich": dict(),
                 "3 Themen (Puffer 6), je 5 Aktien, quartalsweise": dict(freq="BQE"),
                 "4 Themen (Puffer 8), je 5 Aktien, quartalsweise": dict(enter=4, keep=8, freq="BQE")}.items():
    r, turn = run_buf(**kw)
    print(f"{name:50s} 2005–18: {st(r,'2005-01-01','2018-12-31')}")
    print(f"{'':50s} 2019–26: {st(r,'2019-01-01','2026-11-18')} | Umschlag/J {turn['2019':].sum()/8:.1f}")
