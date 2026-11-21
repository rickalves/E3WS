# -*- coding: utf-8 -*-
"""PASSO D3 - Escolher os dias de ruido para treinar o detector (DET) da ISPT.

Versao 2 (baseline do Pablo): usa o ANO INTEIRO de 2014, inclusive o 1o semestre, em que o canal
HHE esta congelado e tem spikes. O detector precisa aprender que isso tambem e ruido.

Regras:
  1. o dia precisa estar completo nos 3 canais (>= 23,9 h de dado);
  2. fora o dia 189 (08/07/2014), em que o sensor foi trocado de epoca no meio do dia;
  3. fora dias com evento do catalogo IG-EPN a menos de 300 km da ISPT;
  4. fora dias com telessismo M >= 6,5 no mundo (USGS) e o dia seguinte se o telessismo foi
     depois das 21 h (as ondas de superficie duram horas);
  5. dos dias que sobram, sorteia N POR MES (padrao 2): um da 1a quinzena e um da 2a, para cobrir
     o ano todo e as duas situacoes do HHE (congelado e normal).
Os dias candidatos que nao forem sorteados ficam marcados como "validacao".

Uso (a partir de experimentos/exp02_ispt_2014):
  python scripts/escolher_dias_ruido.py <cobertura.csv> <cat_origen_IGEPN.txt> <usgs_mundo.csv> <saida.csv> [N_por_mes]
Exemplo:
  python scripts/escolher_dias_ruido.py results/cobertura_dados_2014.csv ^
      "D:/Downloads/E3WS_Ecuador/E3WS_Ecuador/old/Catalogo/pb_csv/cat_origen_2012_sep2023.txt" ^
      results/usgs_mundo_M6.5_2014.csv results/dias_ruido.csv 2
"""
import sys                                       # argumentos da linha de comando
import numpy as np                               # contas e sorteio
import pandas as pd                              # tabelas
from obspy.geodetics import gps2dist_azimuth     # distancia entre dois pontos na Terra

LAT, LON = -1.262263, -81.0748                   # posicao da estacao ISPT
DIA_TROCA = 189                                  # dia juliano da troca de epoca do sensor (08/07/2014)
SEMENTE = 30002                                  # semente do sorteio (mesma do Pablo): o resultado e sempre igual

# --- Ler os argumentos ---
arq_cobertura = sys.argv[1]                      # CSV do passo B1 (horas de dado por dia e canal)
arq_igepn = sys.argv[2]                          # catalogo IG-EPN (origens)
arq_usgs = sys.argv[3]                           # telessismos M >= 6,5 de 2014 (USGS)
arq_saida = sys.argv[4]                          # onde salvar a tabela de dias
n_por_mes = int(sys.argv[5]) if len(sys.argv) > 5 else 2   # quantos dias sortear por mes

# --- 1. Dias completos nos 3 canais ---
cob = pd.read_csv(arq_cobertura)                 # uma linha por arquivo (dia x canal)
horas_min = cob.groupby("dia")["horas"].min()    # para cada dia, o canal com MENOS horas
dias = pd.DataFrame({"dia": horas_min.index, "horas_min": horas_min.values})   # tabela por dia
dias["data"] = pd.to_datetime("2014-01-01") + pd.to_timedelta(dias.dia - 1, unit="D")  # dia juliano -> data
dias["completo"] = dias.horas_min >= 23.9        # regra 1
dias["troca_sensor"] = dias.dia == DIA_TROCA     # regra 2
dias["hhe_congelado"] = dias.dia <= DIA_TROCA    # so informativo: HHE congelado ate o dia 189

# --- 2. Eventos do IG-EPN perto da ISPT ---
cat = pd.read_csv(arq_igepn, comment="#", skipinitialspace=True, index_col=False)   # index_col=False: as linhas tem 1 coluna a mais
cat.columns = [c.strip() for c in cat.columns]   # tira espacos dos nomes das colunas
cat["t"] = pd.to_datetime(cat["time_value"].str.strip())   # texto -> data/hora
cat = cat[cat.t.dt.year == 2014]                 # so 2014
cat["dist_km"] = [gps2dist_azimuth(LAT, LON, la, lo)[0] / 1000   # distancia ate a ISPT em km
                  for la, lo in zip(cat.latitude_value, cat.longitude_value)]
dias_igepn = set(cat[cat.dist_km < 300].t.dt.dayofyear)   # dias com evento a < 300 km
dias["evento_igepn"] = dias.dia.isin(dias_igepn)  # regra 3

# --- 3. Telessismos ---
usgs = pd.read_csv(arq_usgs)                     # lista do USGS
usgs["t"] = pd.to_datetime(usgs.time)            # texto -> data/hora
dias_tele = set(usgs.t.dt.dayofyear)             # o proprio dia do telessismo
dias_tele |= set(usgs[usgs.t.dt.hour >= 21].t.dt.dayofyear + 1)   # e o dia seguinte, se foi tarde
dias["telessismo"] = dias.dia.isin(dias_tele)    # regra 4

# --- 4. Candidatos = passam em todas as regras ---
dias["candidato"] = dias.completo & ~dias.troca_sensor & ~dias.evento_igepn & ~dias.telessismo

# --- 5. Sorteio: n_por_mes dias por mes, espalhados no mes ---
rng = np.random.default_rng(SEMENTE)             # gerador de numeros aleatorios com semente fixa
treino = []                                      # lista dos dias sorteados
for mes in range(1, 13):                         # para cada mes...
    cand_mes = dias[dias.candidato & (dias.data.dt.month == mes)].sort_values("dia")   # ...candidatos do mes
    for parte in np.array_split(cand_mes, n_por_mes):   # ...divide em n_por_mes pedacos (ex.: 2 quinzenas)
        if len(parte):                           # ...se o pedaco tem algum candidato,
            treino.append(int(rng.choice(parte.dia.values)))   # ...sorteia um dia dele

# --- 6. Marcar o uso de cada dia e salvar ---
dias["uso"] = "excluido"                         # por padrao, excluido
dias.loc[dias.candidato, "uso"] = "validacao"    # candidatos nao sorteados = validacao
dias.loc[dias.dia.isin(treino), "uso"] = "treino"   # sorteados = treino
dias.to_csv(arq_saida, index=False)              # salva a tabela

# --- 7. Resumo na tela ---
print("Dias no ano: %d | completos: %d | candidatos: %d" % (len(dias), dias.completo.sum(), dias.candidato.sum()))
print("Excluidos por: incompleto %d, troca do sensor %d, evento IG-EPN %d, telessismo %d" % (
    (~dias.completo).sum(), dias.troca_sensor.sum(), dias.evento_igepn.sum(), dias.telessismo.sum()))
t = dias[dias.uso == "treino"]                   # so os dias de treino
print("Dias de treino: %d (%d com HHE congelado, %d com HHE normal)" % (
    len(t), t.hhe_congelado.sum(), (~t.hhe_congelado).sum()))
print(t[["dia", "data", "hhe_congelado"]].to_string(index=False))
