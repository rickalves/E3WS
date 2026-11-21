# -*- coding: utf-8 -*-
"""PASSO D7c - Avaliar a validacao: detector COM HHE (3C) x SEM HHE (NZ).

Le as deteccoes do passo D7b (det_2014DDD.csv de cada detector) e calcula:
  1. EVENTOS DO CATALOGO: para cada evento IG-EPN a < 200 km nos dias de validacao, se cada detector
     o encontrou (uma deteccao com a onda P entre a hora de origem e o tempo de viagem esperado);
  2. DETECCOES POR DIA, para os limiares 0,80, 0,90 e 0,95, separando dias com HHE congelado e normal;
  3. CONCORDANCIA: quantas deteccoes aparecem nos dois detectores (P a menos de 5 s);
  4. FIGURAS: sismogramas de uma amostra de deteccoes dos dias calmos (sem eventos no catalogo),
     para conferir a olho se sao terremotos (onda P e depois S) ou ruido.
Saidas em <pasta_saida>: avaliacao.txt, eventos_catalogo.csv, deteccoes_por_dia.csv e as figuras.

Uso (a partir de experimentos/exp02_ispt_2014):
  python scripts/avaliar_validacao.py <dias_validacao.csv> <cat_origen_IGEPN.txt> <pasta_saida>
Exemplo:
  python scripts/avaliar_validacao.py results/dias_validacao.csv ^
      "D:/Downloads/E3WS_Ecuador/E3WS_Ecuador/old/Catalogo/pb_csv/cat_origen_2012_sep2023.txt" results/avaliacao_validacao
"""
import os                                        # pastas
import sys                                       # argumentos
import numpy as np                               # contas
import pandas as pd                              # tabelas
import obspy                                     # sismogramas (para as figuras)
from obspy import UTCDateTime                    # datas/horas
from obspy.geodetics import gps2dist_azimuth     # distancia
import matplotlib                                # graficos
matplotlib.use("Agg")                            # gera arquivos, sem janela
import matplotlib.pyplot as plt                  # desenho

LAT, LON = -1.262263, -81.0748                   # posicao da ISPT
B = r"D:\Downloads\ISPT_DATA_SEISMO\2014\EC\ISPT\{c}.D\EC.ISPT..{c}.D.2014.{d:03d}"   # dados
DETECTORES = {"3C": "results/validacao_3C", "NZ": "results/validacao_NZ"}   # pasta de cada detector
LIMIARES = (0.80, 0.90, 0.95)                    # limiares avaliados
VP = 5.5                                         # velocidade media da onda P (km/s), para o tempo de viagem

arq_dias, arq_cat, saida = sys.argv[1:4]         # argumentos
os.makedirs(saida, exist_ok=True)                # cria a pasta de saida
relatorio = []                                   # linhas do relatorio de texto


def escreve(texto=""):
    """Mostra na tela e guarda no relatorio."""
    print(texto)
    relatorio.append(texto)


# --- Dias de validacao e deteccoes de cada detector ---
dias = pd.read_csv(arq_dias)                     # tabela de dias (grupo A_calmo ou B_com_eventos)
det = {}                                         # deteccoes de cada detector (uma tabela por detector)
for nome, pasta in DETECTORES.items():           # para cada detector...
    tabelas = []                                 # ...junta as deteccoes de todos os dias
    for d in dias.dia:
        t = pd.read_csv(os.path.join(pasta, "det_2014%03d.csv" % d))   # deteccoes do dia
        t["dia"] = d                             # anota o dia
        tabelas.append(t)
    det[nome] = pd.concat(tabelas, ignore_index=True)   # tabela unica
    det[nome]["tP"] = [UTCDateTime(x).timestamp for x in det[nome].P_AI]   # hora da P em segundos

# === 1. Eventos do catalogo ===
cat = pd.read_csv(arq_cat, comment="#", skipinitialspace=True, index_col=False)   # catalogo IG-EPN
cat.columns = [c.strip() for c in cat.columns]   # limpa nomes
cat["t"] = pd.to_datetime(cat["time_value"].str.strip())   # texto -> data/hora
cat = cat[cat.t.dt.year == 2014].copy()          # 2014
cat["dist_km"] = [gps2dist_azimuth(LAT, LON, a, b)[0] / 1000 for a, b in zip(cat.latitude_value, cat.longitude_value)]
cat = cat[(cat.dist_km < 200) & cat.t.dt.dayofyear.isin(dias.dia)].copy()   # eventos a < 200 km nos dias de validacao
linhas = []                                      # uma linha por evento
for _, ev in cat.iterrows():                     # para cada evento...
    t0 = UTCDateTime(str(ev.t)).timestamp        # ...hora de origem
    t_fim = t0 + ev.dist_km / VP + 15            # ...a P deve chegar ate aqui (tempo de viagem + 15 s de folga)
    linha = {"hora": str(ev.t)[:19], "mag": ev.magnitude_value_M, "dist_km": round(ev.dist_km),
             "prof_km": ev.depth_value, "hhe_congelado": ev.t.dayofyear < 189}
    for nome, d in det.items():                  # ...para cada detector
        achou = d[(d.tP >= t0 - 5) & (d.tP <= t_fim)]   # deteccoes com a P na janela esperada
        linha["%s_prob" % nome] = round(achou.prob_p_media3.max(), 3) if len(achou) else 0   # maior forca de disparo
        linha["%s_mag46" % nome] = achou.mag_46s.iloc[0] if len(achou) else np.nan          # magnitude estimada (46 s)
        linha["%s_dis46" % nome] = achou.dis_46s.iloc[0] if len(achou) else np.nan          # distancia estimada (46 s)
    linhas.append(linha)
eventos = pd.DataFrame(linhas)                   # tabela de eventos
eventos.to_csv(os.path.join(saida, "eventos_catalogo.csv"), index=False)
escreve("=== 1. Eventos do IG-EPN (< 200 km) nos dias de validacao: %d ===" % len(eventos))
escreve(eventos.to_string(index=False))
for lim in LIMIARES:                             # para cada limiar: quantos eventos cada detector achou
    escreve("limiar %.2f: 3C achou %d/%d | NZ achou %d/%d" % (
        lim, (eventos["3C_prob"] >= lim).sum(), len(eventos), (eventos["NZ_prob"] >= lim).sum(), len(eventos)))

# === 2. Deteccoes por dia ===
escreve("\n=== 2. Deteccoes por dia (media) ===")
por_dia = []                                     # tabela dia x detector x limiar
for _, dd in dias.iterrows():                    # para cada dia...
    for nome, d in det.items():                  # ...e cada detector
        for lim in LIMIARES:                     # ...e cada limiar
            n = ((d.dia == dd.dia) & (d.prob_p_media3 >= lim)).sum()   # quantas deteccoes
            por_dia.append({"dia": dd.dia, "grupo": dd.grupo, "hhe_congelado": dd.hhe_congelado,
                            "detector": nome, "limiar": lim, "n_det": n})
por_dia = pd.DataFrame(por_dia)
por_dia.to_csv(os.path.join(saida, "deteccoes_por_dia.csv"), index=False)
resumo = por_dia.pivot_table(index=["grupo", "hhe_congelado"], columns=["detector", "limiar"], values="n_det", aggfunc="mean").round(1)
escreve(resumo.to_string())

# === 3. Concordancia entre os detectores (limiar 0,80) ===
escreve("\n=== 3. Concordancia (P a menos de 5 s), limiar 0,80 ===")
for a, b in (("3C", "NZ"), ("NZ", "3C")):        # nos dois sentidos
    ta = det[a].tP.values; tb = np.sort(det[b].tP.values)   # horas da P
    i = np.searchsorted(tb, ta)                  # posicao de cada P de "a" na lista ordenada de "b"
    dist = np.minimum(np.abs(ta - tb[np.clip(i - 1, 0, len(tb) - 1)]), np.abs(ta - tb[np.clip(i, 0, len(tb) - 1)])) if len(tb) else np.full(len(ta), np.inf)
    escreve("%d de %d deteccoes do %s tambem aparecem no %s" % ((dist < 5).sum(), len(ta), a, b))

# === 4. Figuras de uma amostra de deteccoes dos dias calmos ===
rng = np.random.default_rng(30002)               # sorteio reproduzivel
calmos = set(dias[dias.grupo == "A_calmo"].dia)  # dias calmos
cache = {}                                       # dados ja lidos (para nao ler o mesmo dia varias vezes)
for nome, d in det.items():                      # para cada detector...
    amostra = d[d.dia.isin(calmos) & (d.prob_p_media3 >= 0.80)]   # ...deteccoes dos dias calmos
    if len(amostra) == 0:                        # ...se nao ha nenhuma, nada a desenhar
        escreve("\n%s: nenhuma deteccao nos dias calmos" % nome); continue
    amostra = amostra.iloc[rng.choice(len(amostra), size=min(12, len(amostra)), replace=False)].sort_values("tP")   # ate 12
    fig, ax = plt.subplots(len(amostra), 3, figsize=(15, 1.9 * len(amostra)), squeeze=False)   # grade
    for i, (_, ev) in enumerate(amostra.iterrows()):   # para cada deteccao sorteada...
        if ev.dia not in cache:                  # ...le o dia (uma vez)
            st = obspy.Stream()
            for c in ("HHE", "HHN", "HHZ"):
                st += obspy.read(B.format(c=c, d=int(ev.dia)))
            st.merge(fill_value=0); st.sort(keys=["channel"])
            cache[ev.dia] = st
        tP = UTCDateTime(ev.P_AI)                # hora da P
        tr3 = cache[ev.dia].slice(tP - 10, tP + 30).copy()   # 10 s antes e 30 s depois
        tr3.detrend("demean"); tr3.filter("bandpass", freqmin=1, freqmax=20)   # filtro 1-20 Hz
        for j, tr in enumerate(tr3):             # ...desenha cada componente
            x = np.arange(tr.stats.npts) / tr.stats.sampling_rate - 10   # tempo, 0 = P
            ax[i, j].plot(x, tr.data, "k", lw=0.5)
            ax[i, j].axvline(0, color="r", lw=0.7)   # linha vermelha = P marcada pelo E3WS
            ax[i, j].set_yticks([])
            if i == 0: ax[i, j].set_title(tr.stats.channel)
        ax[i, 0].set_ylabel("%s\nprob %.2f\nM%.1f %0.fkm" % (str(tP)[5:19].replace("T", " "), ev.prob_p_media3,
                                                         ev.mag_46s, ev.dis_46s), fontsize=7)
    for a_ in ax[-1]: a_.set_xlabel("s (0 = P do E3WS)")
    fig.suptitle("Detector %s: amostra de deteccoes em dias SEM eventos no catalogo (1-20 Hz)" % nome)
    plt.tight_layout(); arq = os.path.join(saida, "amostra_deteccoes_%s.png" % nome)
    plt.savefig(arq, dpi=75); plt.close(fig)
    escreve("\nFigura: %s" % arq)

with open(os.path.join(saida, "avaliacao.txt"), "w", encoding="utf8") as f:   # salva o relatorio
    f.write("\n".join(relatorio))
