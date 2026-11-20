"""Compara a rodada do E3WS do Pablo na ISPT (2014) com o catalogo do IG-EPN.

Mostra a queda de ~1000 para ~30 deteccoes/mes em 08/07/2014 (canal HHE morto ate essa data)
e quantas deteccoes coincidem com eventos do catalogo.

Uso: python comparar_pablo_igepn.py <cat_origen_2012_sep2023.txt> <E3WS_ISPT.csv>
Ex.: python scripts/comparar_pablo_igepn.py ^
       "D:/Downloads/E3WS_Ecuador/E3WS_Ecuador/old/Catalogo/pb_csv/cat_origen_2012_sep2023.txt" ^
       "D:/Downloads/E3WS_Ecuador/E3WS_Ecuador/new/Figs/E3WS_ISPT.csv"
"""
import sys
import numpy as np, pandas as pd
from obspy.geodetics import gps2dist_azimuth

LAT, LON = -1.262263, -81.0748
TROCA = pd.Timestamp("2014-07-08 18:30")


def ler_igepn(f):
    # as linhas de dados tem uma coluna a mais que o cabecalho (agencia) -> index_col=False
    c = pd.read_csv(f, comment="#", skipinitialspace=True, index_col=False)
    c.columns = [x.strip() for x in c.columns]
    c["t"] = pd.to_datetime(c["time_value"].str.strip())
    c["dist"] = [gps2dist_azimuth(LAT, LON, a, b)[0] / 1e3 for a, b in zip(c.latitude_value, c.longitude_value)]
    return c


def mais_proximo(t_a, t_b):
    """Para cada tempo em t_a, distancia (s) ate o tempo mais proximo em t_b."""
    tb = np.sort(t_b); i = np.searchsorted(tb, t_a)
    return np.minimum(np.abs(t_a - tb[np.clip(i - 1, 0, len(tb) - 1)]), np.abs(t_a - tb[np.clip(i, 0, len(tb) - 1)]))


if __name__ == "__main__":
    c = ler_igepn(sys.argv[1])
    print("Catalogo IG-EPN (arquivo inteiro): %d eventos, %s a %s, magnitude minima %.1f"
          % (len(c), c.t.min().date(), c.t.max().date(), c.magnitude_value_M.min()))
    c = c[(c.t >= "2014-01-01") & (c.t < "2015-01-01")]
    cc = c[c.dist < 200]
    print("IG-EPN 2014: %d eventos no Equador; %d a < 200 km da ISPT; %d a < 50 km" % (len(c), len(cc), (c.dist < 50).sum()))
    print("IG-EPN < 200 km, por mes:", cc.groupby(cc.t.dt.month).size().to_dict())

    e = pd.read_csv(sys.argv[2]); e["t"] = pd.to_datetime(e.P_AI.str[:19]); e = e[e.t.dt.year == 2014]
    print("\nE3WS do Pablo na ISPT, 2014, por mes:", e.groupby(e.t.dt.month).size().to_dict())
    a, b = e[e.t < TROCA], e[e.t >= TROCA]
    for k in ["P_prob", "mag_pred", "dis_pred"]:
        print("  mediana de %-8s antes / depois de 08/07: %.2f / %.2f" % (k, a[k].median(), b[k].median()))

    te = e.t.values.astype("int64") / 1e9; tc = cc.t.values.astype("int64") / 1e9
    perto = mais_proximo(te, tc) < 60
    antes = (e.t < TROCA).values
    print("\nDeteccoes do E3WS a < 60 s de um evento IG-EPN (< 200 km): antes %d de %d | depois %d de %d"
          % ((perto & antes).sum(), antes.sum(), (perto & ~antes).sum(), (~antes).sum()))
    achados = mais_proximo(tc, te) < 60
    print("Eventos IG-EPN (< 200 km) encontrados pelo E3WS: %d de %d" % (achados.sum(), len(tc)))
