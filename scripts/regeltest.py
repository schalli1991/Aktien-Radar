"""Test Aktien-tauglicher Regeln gegen Halten (mit 0.5 % Gebühr pro Kauf/Verkauf)."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import kalibrierung as K

ROOT = Path(__file__).resolve().parents[1]
FEE = 0.005
PERIODEN = [("2005–2018", "2005-01-01", "2018-12-31"), ("2019–2026", "2019-01-01", "2026-11-18")]

def panel():
    kurse = K.lade_kurse()
    roh = pd.read_parquet(ROOT / "daten" / "kurse.parquet")
    idx = pd.bdate_range("2003-01-01", roh.index[-1])
    P = pd.DataFrame({t: s.reindex(idx).ffill(limit=5) for t, s in kurse.items()})
    I = {t: K.bereinige(roh[t]).reindex(idx).ffill(limit=5) for t in ["^GSPC", "^SSMI", "^GDAXI", "^STOXX50E"]}
    return kurse, P, I

def index_fuer(t):
    if t.endswith(".SW"): return "^SSMI"
    if t.endswith(".DE"): return "^GDAXI"
    if any(t.endswith(x) for x in (".PA", ".AS", ".BR", ".MI", ".MC", ".CO")): return "^STOXX50E"
    return "^GSPC"

def kennzahlen(r):
    r = r.dropna()
    eq = (1 + r).cumprod()
    j = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / j) - 1
    mdd = (eq / eq.cummax() - 1).min()
    vol = r.std() * np.sqrt(252)
    return cagr * 100, mdd * 100, (cagr / vol if vol else np.nan)

def main():
    kurse, P, I = panel()
    mod = json.load(open(ROOT / "modell" / "varianten.json"))["C-vol-ema10"]
    R = pd.DataFrame({t: K.risk(s, mod).reindex(P.index).ffill(limit=5) for t, s in kurse.items()})
    ret = P.pct_change(fill_method=None)
    sma200, sma50 = P.rolling(200, min_periods=200).mean(), P.rolling(50, min_periods=50).mean()
    Isma = {k: v.rolling(200, min_periods=200).mean() for k, v in I.items()}

    # ---- Timing-Regeln je Aktie: Position 0..1, Signal am Schluss t gilt ab t+1
    pos = {}
    pos["Halten"] = pd.DataFrame(1.0, index=P.index, columns=P.columns).where(P.notna())
    # Trendfilter 200 Tage mit 2 % Band
    t200 = pd.DataFrame(np.nan, index=P.index, columns=P.columns)
    t200[P > sma200 * 1.02] = 1.0; t200[P < sma200 * 0.98] = 0.0
    pos["Trendfilter 200T"] = t200.ffill().where(P.notna())
    # Trendbruch nach heisser Phase: nach Risk >= 90 Verkauf beim Schluss unter SMA50, Wiedereinstieg über SMA50
    tb = np.ones(P.shape)
    Pv, Rv, S50 = P.values, R.values, sma50.values
    for j in range(P.shape[1]):
        armed, inv = False, 1.0
        for i in range(P.shape[0]):
            r, p, s = Rv[i, j], Pv[i, j], S50[i, j]
            if np.isnan(p) or np.isnan(s):
                tb[i, j] = inv; continue
            if not np.isnan(r) and r >= 90: armed = True
            if inv == 1.0 and armed and p < s: inv, armed = 0.0, False
            elif inv == 0.0 and p > s: inv = 1.0
            tb[i, j] = inv
    pos["Trendbruch nach Risk 90"] = pd.DataFrame(tb, index=P.index, columns=P.columns).where(P.notna())
    pos["Halbe Position ab Risk 95"] = pd.DataFrame(np.where(R.values >= 95, 0.5, 1.0), index=P.index, columns=P.columns).where(P.notna())
    mk = pd.DataFrame(index=P.index, columns=P.columns, dtype=float)
    for t in P.columns:
        k = index_fuer(t); mk[t] = (I[k] > Isma[k]).astype(float).where(Isma[k].notna(), 1.0)
    pos["Marktfilter (Index über 200T)"] = mk.where(P.notna())

    zeilen = []
    for name, ps in pos.items():
        ps = ps.fillna(0.0)
        handel = ps.diff().abs().fillna(0.0)
        r_stock = ps.shift(1) * ret - handel.shift(1).fillna(0) * FEE
        r_stock = r_stock.where(P.shift(1).notna())
        for pn, a, b in PERIODEN:
            m = (P.index >= a) & (P.index <= b)
            sub = r_stock.loc[m]
            ok = sub.notna().sum() > 0.8 * m.sum()
            sub = sub.loc[:, ok]
            port = sub.mean(axis=1)
            cagr, mdd, sh = kennzahlen(port)
            # je Aktie: Endvermögen vs. Halten
            eq = (1 + sub.fillna(0)).prod()
            zeilen.append(dict(art="Timing", regel=name, periode=pn, n=int(ok.sum()), cagr=cagr, mdd=mdd, rendite_risiko=sh,
                               eq=eq))
    halten = {z["periode"]: z["eq"] for z in zeilen if z["regel"] == "Halten"}
    for z in zeilen:
        e = z.pop("eq"); h = halten[z["periode"]].reindex(e.index)
        z["schlägt_halten_%"] = float((e > h).mean() * 100); z["median_verhältnis"] = float((e / h).median())

    # ---- Rotation: monatlich, Top 20
    me = P.resample("BME").last().index
    me = [d for d in me if d in P.index]
    mom = P.shift(21) / P.shift(252) - 1
    def rotation(auswahl, marktfilter=False):
        w = pd.DataFrame(0.0, index=P.index, columns=P.columns)
        cur = pd.Series(0.0, index=P.columns)
        for d in P.index:
            if d in me_set:
                sel = auswahl(d)
                cur = pd.Series(0.0, index=P.columns)
                if len(sel) and (not marktfilter or I["^GSPC"][d] > Isma["^GSPC"][d]):
                    cur[sel] = 1.0 / len(sel)
            w.loc[d] = cur
        return w
    me_set = set(me)
    def ew(d):
        return P.columns[P.loc[d].notna() & mom.loc[d].notna()]
    def top_mom(d, rmax=None):
        m = mom.loc[d].dropna()
        if rmax is not None: m = m[R.loc[d, m.index] < rmax]
        return m.nlargest(20).index
    def tief_im_trend(d):
        ok = (P.loc[d] > sma200.loc[d]) & R.loc[d].notna()
        return R.loc[d][ok].nsmallest(20).index
    rot = {"Alle gleich gewichtet (Vergleich)": rotation(ew),
           "Momentum Top 20": rotation(top_mom),
           "Momentum Top 20 ohne Risk 90+": rotation(lambda d: top_mom(d, 90)),
           "Momentum Top 20 + Marktfilter": rotation(top_mom, True),
           "Tiefster Risk über 200T, Top 20": rotation(tief_im_trend)}
    for name, w in rot.items():
        turn = w.diff().abs().sum(axis=1).fillna(0)
        r = (w.shift(1) * ret.fillna(0)).sum(axis=1) - turn.shift(1).fillna(0) * FEE
        for pn, a, b in PERIODEN:
            m = (P.index >= a) & (P.index <= b)
            cagr, mdd, sh = kennzahlen(r[m])
            zeilen.append(dict(art="Rotation", regel=name, periode=pn, n=20, cagr=cagr, mdd=mdd, rendite_risiko=sh))
    df = pd.DataFrame(zeilen)
    df.to_csv(ROOT / "berichte" / "regeltest_tabelle.csv", sep=";", index=False, float_format="%.3f")
    pd.set_option("display.width", 220)
    print(df.round(2).to_string())

    # ---- Einstieg: tiefer Score + Wende (Schluss über SMA20) vs. beliebiger Tag
    sma20 = P.rolling(20).mean()
    sig = (R.shift(1) < 20) & (P > sma20) & (P.shift(1) <= sma20.shift(1))
    for h in (60, 120, 250):
        f = P.shift(-h) / P - 1
        for pn, a, b in PERIODEN:
            m = (P.index >= a) & (P.index <= b)
            fs, ss = f.loc[m], sig.loc[m]
            ex = (fs - fs.mean())[ss].stack().dropna()
            print(f"Einstieg tiefer Risk + Wende, {pn}, {h}T: n={len(ex)}, Überrendite Mittel {ex.mean()*100:.2f} %, Median {ex.median()*100:.2f} %, Anteil positiv {(ex>0).mean()*100:.0f} %")

if __name__ == "__main__":
    main()
