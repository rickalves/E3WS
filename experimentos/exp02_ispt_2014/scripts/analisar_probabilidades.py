# -*- coding: utf-8 -*-
"""Analisa as probabilidades salvas pelo e3ws_dia.py (prob_2014DDD.csv.gz) de um detector.

Objetivo: entender por que ha poucas deteccoes. Para cada dia mostra:
  - quantas janelas tem prob. de P >= 0,5 e >= 0,8, e prob. de S >= 0,8;
  - quantos "candidatos" existem: momentos em que a media das 3 ultimas prob. de P passa de 0,8
    (sem a regra de rearme);
  - quantas deteccoes saem COM a regra de rearme do E3WS (media das 5 ultimas prob. de ruido >= 0,99);
  - quanto tempo do dia o gatilho fica "travado" (disparado, esperando para rearmar);
  - quantas janelas tem prob. de ruido >= 0,99 (condicao para rearmar).

Uso (a partir de experimentos/exp02_ispt_2014):
  python scripts/analisar_probabilidades.py <pasta_validacao> <dias_validacao.csv> [limiar]
Exemplo:
  python scripts/analisar_probabilidades.py results/validacao_NZ results/dias_validacao.csv 0.80
"""
import os                                        # caminhos
import sys                                       # argumentos
import numpy as np                               # contas
import pandas as pd                              # tabelas

pasta, arq_dias = sys.argv[1], sys.argv[2]       # pasta com prob_*.csv.gz e tabela de dias
limiar = float(sys.argv[3]) if len(sys.argv) > 3 else 0.80   # limiar do gatilho
dias = pd.read_csv(arq_dias)                     # dias de validacao

linhas = []                                      # uma linha de resultado por dia
for _, d in dias.iterrows():                     # para cada dia...
    p = pd.read_csv(os.path.join(pasta, "prob_2014%03d.csv.gz" % d.dia))   # ...probabilidades de cada janela
    pn, pp, ps = p.prob_n.values, p.prob_p.values, p.prob_s.values          # ...ruido, P, S
    media3_p = pd.Series(pp).rolling(3).mean().values   # media das 3 ultimas prob. de P (em cada janela)
    media5_n = pd.Series(pn).rolling(5).mean().values   # media das 5 ultimas prob. de ruido
    acima = np.nan_to_num(media3_p) >= limiar    # janelas em que a media de P esta acima do limiar
    candidatos = int(np.sum(acima[1:] & ~acima[:-1]))   # quantas vezes ela CRUZA o limiar (subida)

    # Gatilho com rearme (mesma logica do e3ws_dia.py, simplificada: sem tratar falhas de dados)
    disparado, antes, n_det, travado = 0, 0, 0, 0   # estado, estado anterior, deteccoes, janelas travadas
    for k in range(len(pp)):                     # percorre as janelas
        if np.isnan(pp[k]):                      # janela ruim (falha de dados): reinicia
            disparado = antes = 0; continue
        if acima[k]:                             # media de P acima do limiar -> dispara
            disparado = 1
        if disparado and media5_n[k] >= 0.99:    # media de ruido >= 0,99 -> rearma
            disparado = 0
        if antes == 0 and disparado == 1:        # acabou de disparar -> deteccao
            n_det += 1
        travado += disparado                     # conta o tempo disparado
        antes = disparado

    linhas.append({"dia": d.dia, "grupo": d.grupo, "hhe_congelado": d.hhe_congelado,
                   "P>=0.5": int((pp >= 0.5).sum()), "P>=0.8": int((pp >= 0.8).sum()),
                   "S>=0.8": int((ps >= 0.8).sum()), "candidatos": candidatos,
                   "deteccoes": n_det, "travado_h": round(travado / 3600, 2),
                   "ruido>=0.99_%": round(100 * np.nanmean(pn >= 0.99), 1),
                   "ruido_mediana": round(float(np.nanmedian(pn)), 3)})

tab = pd.DataFrame(linhas)                       # tabela final
print("Pasta: %s | limiar %.2f" % (pasta, limiar))
print(tab.to_string(index=False))                # mostra
tab.to_csv(os.path.join(pasta, "analise_probabilidades.csv"), index=False)   # salva
