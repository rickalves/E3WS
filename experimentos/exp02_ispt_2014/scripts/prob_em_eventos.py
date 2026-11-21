# -*- coding: utf-8 -*-
"""Mostra a probabilidade de P/S do detector da ISPT em volta de eventos do catalogo IG-EPN.

Para cada evento do IG-EPN a < 200 km num dia escolhido: calcula as features e as probabilidades
do detector de 60 s antes a 120 s depois da hora de origem e mostra a maior prob. de P e de S.
Serve para checar, rapidamente, se o detector "enxerga" eventos conhecidos.

Uso (a partir de experimentos/exp02_ispt_2014):
  python scripts/prob_em_eventos.py <cat_origen_IGEPN.txt> <3C ou NZ> <dia1> [dia2 ...]
"""
import sys, __main__                              # argumentos; __main__ para abrir os modelos
import numpy as np                                # contas
import pandas as pd                               # tabelas
from obspy import UTCDateTime                     # datas/horas
from obspy.geodetics import gps2dist_azimuth      # distancia
sys.path.insert(0, "scripts")                     # para importar o e3ws_dia
import e3ws_dia as e                              # reaproveita leitura, janelas e modelos
__main__.pb_SAM = e.pb_SAM                        # necessario para abrir os modelos de fonte

cat = pd.read_csv(sys.argv[1], comment="#", skipinitialspace=True, index_col=False)   # catalogo IG-EPN
cat.columns = [c.strip() for c in cat.columns]    # limpa nomes
cat["t"] = pd.to_datetime(cat["time_value"].str.strip())   # texto -> data/hora
cat = cat[cat.t.dt.year == 2014].copy()           # 2014
cat["dist_km"] = [gps2dist_azimuth(e.STA_LAT, e.STA_LON, a, b)[0] / 1000 for a, b in zip(cat.latitude_value, cat.longitude_value)]
TIPO = sys.argv[2].upper()                         # qual detector: 3C (3 componentes) ou NZ (so N e Z)
M = e.modelos(TIPO)                               # modelos
for dia in [int(d) for d in sys.argv[3:]]:        # para cada dia pedido...
    st = e.ler_dia(dia)                           # ...le o dia
    evs = cat[(cat.t.dt.dayofyear == dia) & (cat.dist_km < 200)]   # ...eventos do dia a < 200 km
    for _, ev in evs.iterrows():                  # ...para cada evento
        t0 = UTCDateTime(str(ev.t))               # hora de origem
        feats = []                                # features das janelas
        for k in range(-60, 120):                 # de 60 s antes a 120 s depois
            w = st.slice(t0 + k, t0 + k + 10)     # janela de 10 s
            if e.janela_boa(w):                   # se e boa,
                feats.append(np.real(e.pb_utils.st_FV(w, True, pzfile=M["INV"], fmin=1.0, fmax=7.0)))   # features
        p = M["DET"].predict_proba(np.array(feats)[:, M["COLS"]])   # probabilidades (so as features do detector)
        print("[%s] dia %3d %s M%.1f %3.0f km prof %3.0f km | max P %.3f | max S %.3f | HHE congelado: %s" % (
            TIPO, dia, str(ev.t)[:19], ev.magnitude_value_M, ev.dist_km, ev.depth_value, p[:, 1].max(), p[:, 2].max(), dia < 189))
