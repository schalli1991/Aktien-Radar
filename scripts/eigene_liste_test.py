"""Test: Momentum innerhalb einer eigenen Themenliste. Viele Zufallslisten aus Tech-, KI-, Fintech- und Energiethemen.
Vergleich je Liste: alle Titel gleich gewichtet halten vs. nur die stärksten (Puffer-Regel), monatlich, 1.5 % Gebühr."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np, pandas as pd, kalibrierung as K
ROOT = Path(__file__).resolve().parents[1]
THEMEN = ["Erneuerbare & Versorger", "Internet & Plattformen", "KI & Halbleiter", "Fintech & Krypto", "Software & Cloud", "Quantencomputing", "Tech-Hardware", "Cybersecurity"]
cfg = pd.read_csv(ROOT / "config" / "yuh_aktien.csv", sep=";", dtype=str).set_index("ticker")
kurse = K.lade_kurse()
pool = [t for t in kurse if cfg.at[t, "thema"] in THEMEN]
M = pd.DataFrame({t: kurse[t] for t in pool}).resample("ME").last()
R = M.pct_change(fill_method=None).values
MOM = (M.shift(1) / M.shift(12) - 1).values
dates = M.index
rng = np.random.default_rng(1)
FEE = 0.015
def run(cols, a, b, top, keep):
    idx = np.where((dates >= a) & (dates <= b))[0]
    w_ew = np.zeros(len(cols)); w_m = np.zeros(len(cols)); held = []
    eq_e = eq_m = 1.0; pe = pm = 1.0; mdd_e = mdd_m = 0.0; tr = 0.0
    for k in idx[:-1]:
        ok = ~np.isnan(MOM[k, cols]) & ~np.isnan(R[k + 1, cols]) if k + 1 < len(dates) else None
        # gleich gewichtet: alle verfügbaren
        av = np.where(~np.isnan(M.values[k, cols]) & ~np.isnan(R[k + 1, cols]))[0]
        ne = np.zeros(len(cols)); ne[av] = 1 / len(av) if len(av) else 0
        cost_e = np.abs(ne - w_ew).sum() * FEE * (0 if k == idx[0] else 1)
        # Momentum mit Puffer
        m = MOM[k, cols].copy(); m[~ok] = np.nan
        valid = np.where(~np.isnan(m))[0]
        order = valid[np.argsort(-m[valid])]; rank = {j: r + 1 for r, j in enumerate(order)}
        held = [j for j in held if j in rank and rank[j] <= keep]
        for j in order:
            if len(held) >= top: break
            if j not in held: held.append(j)
        nm = np.zeros(len(cols)); 
        if held: nm[held] = 1 / len(held)
        cost_m = np.abs(nm - w_m).sum() * FEE
        r = np.nan_to_num(R[k + 1, cols])
        eq_e *= (1 + ne @ r - cost_e); eq_m *= (1 + nm @ r - cost_m); tr += np.abs(nm - w_m).sum()
        pe, pm = max(pe, eq_e), max(pm, eq_m); mdd_e, mdd_m = min(mdd_e, eq_e / pe - 1), min(mdd_m, eq_m / pm - 1)
        w_ew = ne * (1 + r) / max(1e-9, 1 + ne @ r); w_m = nm * (1 + r) / max(1e-9, 1 + nm @ r)
    j = len(idx[:-1]) / 12
    return eq_e ** (1 / j) - 1, eq_m ** (1 / j) - 1, mdd_e, mdd_m, tr / j
print(f"Pool: {len(pool)} Titel aus {len(THEMEN)} Themen")
for a, b in (("2005-01-01", "2018-12-31"), ("2019-01-01", "2026-10-31")):
    avail = [i for i, t in enumerate(pool) if M[t].loc[:pd.Timestamp(a) - pd.DateOffset(months=13)].notna().any()]
    for n, top, keep in ((12, 4, 6), (12, 6, 9), (20, 5, 10), (20, 8, 14)):
        res = np.array([run(list(rng.choice(avail, n, replace=False)), pd.Timestamp(a), pd.Timestamp(b), top, keep) for _ in range(400)])
        d = res[:, 1] - res[:, 0]
        print(f"{a[:4]}–{b[:4]} | Liste {n}, halte Top {top} (bis Rang {keep}) | Titel verfügbar {len(avail)} | "
              f"alle halten {np.median(res[:,0])*100:5.1f} % | Momentum {np.median(res[:,1])*100:5.1f} % | "
              f"Differenz Median {np.median(d)*100:+5.1f} Pp, Momentum besser in {(d>0).mean()*100:3.0f} % der Listen | "
              f"MDD {np.median(res[:,2])*100:4.0f} % vs {np.median(res[:,3])*100:4.0f} % | Umschlag/J {np.median(res[:,4]):.1f}")
