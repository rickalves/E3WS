# -*- coding: utf-8 -*-
"""PASSO D7a - Escolher os dias para validar o detector (DET) da ISPT.

Dois grupos, metade em cada semestre (HHE congelado x HHE normal):
  A. "calmos": dias marcados como "validacao" no passo D3 (sem evento IG-EPN a < 300 km, sem
     telessismo) e que NAO entraram no treino. Servem para ver quantas deteccoes aparecem
     num dia sem eventos conhecidos (podem ser microssismos reais ou alarmes falsos).
  B. "com eventos": dias completos com eventos do IG-EPN a < 200 km da ISPT. Servem para medir
     quantos eventos conhecidos o E3WS encontra. Escolhe os dias com mais eventos.
O dia 2014-06-13 (evento USGS mb 4,4 a 11 km, usado no passo C3) entra sempre no grupo B.

Uso (a partir de experimentos/exp02_ispt_2014):
  python scripts/escolher_dias_validacao.py <dias_ruido.csv> <cat_origen_IGEPN.txt> <saida.csv> [n_por_grupo_semestre]
Exemplo:
  python scripts/escolher_dias_validacao.py results/dias_ruido.csv ^
      "D:/Downloads/E3WS_Ecuador/E3WS_Ecuador/old/Catalogo/pb_csv/cat_origen_2012_sep2023.txt" ^
      results/dias_validacao.csv 3
"""
import sys                                       # argumentos da linha de comando
import numpy as np                               # sorteio
import pandas as pd                              # tabelas
from obspy.geodetics import gps2dist_azimuth     # distancia entre dois pontos

LAT, LON = -1.262263, -81.0748                   # posicao da ISPT
DIA_TROCA = 189                                  # troca de epoca do sensor (08/07/2014)
DIA_TESTE = 164                                  # 2014-06-13, evento mb 4,4 a 11 km (passo C3)

arq_dias, arq_igepn, arq_saida = sys.argv[1:4]   # entradas e saida
n = int(sys.argv[4]) if len(sys.argv) > 4 else 3 # dias por grupo e por semestre

dias = pd.read_csv(arq_dias)                     # tabela do passo D3 (uso = treino/validacao/excluido)
rng = np.random.default_rng(30002)               # sorteio reproduzivel

# --- Grupo A: calmos (sorteio entre os dias de validacao de cada semestre) ---
calmos = []                                      # lista de dias do grupo A
for semestre in (dias.dia < DIA_TROCA, dias.dia > DIA_TROCA):   # 1o e 2o semestre
    cand = dias[(dias.uso == "validacao") & semestre].dia.values # candidatos do semestre
    calmos += sorted(rng.choice(cand, size=n, replace=False).tolist())   # sorteia n dias

# --- Grupo B: dias com mais eventos IG-EPN a < 200 km ---
cat = pd.read_csv(arq_igepn, comment="#", skipinitialspace=True, index_col=False)   # catalogo
cat.columns = [c.strip() for c in cat.columns]   # limpa nomes das colunas
cat["t"] = pd.to_datetime(cat["time_value"].str.strip())   # texto -> data/hora
cat = cat[cat.t.dt.year == 2014].copy()          # so 2014
cat["dist_km"] = [gps2dist_azimuth(LAT, LON, a, b)[0] / 1000   # distancia ate a ISPT
                  for a, b in zip(cat.latitude_value, cat.longitude_value)]
perto = cat[cat.dist_km < 200]                   # eventos a < 200 km
por_dia = perto.groupby(perto.t.dt.dayofyear).size()   # quantos eventos por dia
completos = set(dias[dias.completo].dia)         # dias com dado completo
com_eventos = [DIA_TESTE]                        # o dia do teste C3 sempre entra
for semestre in (lambda d: d < DIA_TROCA, lambda d: d > DIA_TROCA):   # 1o e 2o semestre
    cand = [d for d in por_dia.sort_values(ascending=False).index     # do dia com mais eventos...
            if semestre(d) and d in completos and d != DIA_TESTE]     # ...ao com menos, no semestre
    com_eventos += cand[:n]                      # pega os n primeiros
com_eventos = sorted(set(com_eventos))           # tira repeticoes e ordena

# --- Salvar ---
linhas = [{"dia": d, "grupo": "A_calmo"} for d in calmos] + \
         [{"dia": d, "grupo": "B_com_eventos", "n_eventos_igepn_200km": int(por_dia.get(d, 0))} for d in com_eventos]
tab = pd.DataFrame(linhas)                       # tabela final
tab["data"] = (pd.to_datetime("2014-01-01") + pd.to_timedelta(tab.dia - 1, unit="D")).dt.date   # data legivel
tab["hhe_congelado"] = tab.dia < DIA_TROCA       # informativo
tab.to_csv(arq_saida, index=False)               # salva
print(tab.to_string(index=False))                # mostra
