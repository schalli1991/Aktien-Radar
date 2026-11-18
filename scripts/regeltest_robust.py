import sys, json; sys.path.insert(0,'scripts')
import numpy as np, pandas as pd, regeltest as RT, kalibrierung as K
kurse,P,I=RT.panel(); ret=P.pct_change(fill_method=None).fillna(0)
Isma=I["^GSPC"].rolling(200).mean()
def run(lookback=252, skip=21, topn=20, freq="BME", fee=0.005, univ=None, mf=False):
    cols=P.columns if univ is None else [c for c in P.columns if univ(c)]
    Pc=P[cols]; mom=Pc.shift(skip)/Pc.shift(lookback)-1
    rb=set(d for d in Pc.resample(freq).last().index if d in Pc.index)
    W=np.zeros(Pc.shape); cur=np.zeros(len(cols)); ix={c:i for i,c in enumerate(cols)}
    for k,d in enumerate(Pc.index):
        if d in rb:
            cur=np.zeros(len(cols))
            if not mf or I["^GSPC"][d]>Isma[d]:
                m=mom.loc[d].dropna()
                if len(m)>=topn:
                    for c in m.nlargest(topn).index: cur[ix[c]]=1/topn
        W[k]=cur
    W=pd.DataFrame(W,index=Pc.index,columns=cols)
    turn=W.diff().abs().sum(axis=1).fillna(0)
    r=(W.shift(1)*ret[cols]).sum(axis=1)-turn.shift(1).fillna(0)*fee
    ew=ret[cols].where(Pc.shift(1).notna()&mom.notna()).mean(axis=1)
    return r, ew, turn
def stats(r,ew,a,b):
    m=(r.index>=a)&(r.index<=b); c1=RT.kennzahlen(r[m]); c2=RT.kennzahlen(ew[m])
    yr=pd.DataFrame({'s':r[m],'e':ew[m]}).groupby(r[m].index.year).apply(lambda x:((1+x).prod()-1))
    return f"CAGR {c1[0]:5.1f} vs EW {c2[0]:5.1f} | MDD {c1[1]:6.1f} vs {c2[1]:6.1f} | Jahre besser {(yr.s>yr.e).sum()}/{len(yr)}"
tests={
 "Basis 12-1, Top20, monatlich":dict(),
 "Gebühr 1.5% (inkl. Yuh-Devisen)":dict(fee=0.015),
 "Quartalsweise, Gebühr 1.5%":dict(freq="BQE",fee=0.015),
 "6-1 Monate":dict(lookback=126),
 "Top 10":dict(topn=10),
 "Top 40":dict(topn=40),
 "nur Schweiz+Europa":dict(univ=lambda c:'.' in c and not c.endswith('.KS')),
 "nur USA":dict(univ=lambda c:'.' not in c),
}
for name,kw in tests.items():
    r,ew,turn=run(**kw)
    print(f"{name:34s} 2005–18: {stats(r,ew,'2005-01-01','2018-12-31')}")
    print(f"{'':34s} 2019–26: {stats(r,ew,'2019-01-01','2026-11-18')}   Umschlag/Jahr {turn['2019':].sum()/8:.1f}")
# Beitrag der grössten Gewinner 2019-26
r,ew,turn=run()
print("---- Puffer-Regel: kaufen Top 20, halten bis Rang > 40; Gebühr 1.5 %")
def run_buf(fee=0.015, freq="BME", univ=None, enter=20, exit_=40, lookback=252):
    cols=P.columns if univ is None else [c for c in P.columns if univ(c)]
    Pc=P[cols]; mom=Pc.shift(21)/Pc.shift(lookback)-1
    rb=set(d for d in Pc.resample(freq).last().index if d in Pc.index)
    held=set(); W=np.zeros(Pc.shape); cur=np.zeros(len(cols)); ix={c:i for i,c in enumerate(cols)}
    for k,d in enumerate(Pc.index):
        if d in rb:
            m=mom.loc[d].dropna()
            if len(m)>=exit_:
                rk=m.rank(ascending=False)
                held={c for c in held if c in rk.index and rk[c]<=exit_}
                for c in m.nlargest(enter).index:
                    if len(held)>=enter: break
                    held.add(c)
                cur=np.zeros(len(cols))
                for c in held: cur[ix[c]]=1/len(held)
        W[k]=cur
    W=pd.DataFrame(W,index=Pc.index,columns=cols)
    turn=W.diff().abs().sum(axis=1).fillna(0)
    r=(W.shift(1)*ret[cols]).sum(axis=1)-turn.shift(1).fillna(0)*fee
    ew=ret[cols].where(Pc.shift(1).notna()&mom.notna()).mean(axis=1)
    return r,ew,turn
alt=set(c for c in P.columns if P[c].first_valid_index() is not None and P[c].first_valid_index()<pd.Timestamp('2015-01-01'))
for name,kw in {"Puffer monatlich":dict(),"Puffer quartalsweise":dict(freq="BQE"),
                "Puffer, nur Titel mit Kursen vor 2015":dict(univ=lambda c:c in alt),
                "Puffer, Schweiz+Europa":dict(univ=lambda c:'.' in c and not c.endswith('.KS'))}.items():
    r,ew,turn=run_buf(**kw)
    print(f"{name:40s} 2005–18: {stats(r,ew,'2005-01-01','2018-12-31')}")
    print(f"{'':40s} 2019–26: {stats(r,ew,'2019-01-01','2026-11-18')}   Umschlag/Jahr {turn['2019':].sum()/8:.1f}")
r,ew,turn=run(fee=0.015, univ=lambda c:c in alt)
print(f"{'Basis, Gebühr 1.5%, Titel vor 2015':40s} 2019–26: {stats(r,ew,'2019-01-01','2026-11-18')}")
