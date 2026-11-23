# -*- coding: utf-8 -*-
"""Compara a deteccao das 15:03 do dia 164 (13/06/2014) com um terremoto real do mesmo dia.

Painel de cima: 15:02:50 + 120 s (deteccao que nao esta em nenhum catalogo).
Painel de baixo: 18:10:20 + 120 s (M4,6 a 14 km, IG-EPN).
O HHE e mostrado em contagens brutas (para ver o congelamento); N e Z filtrados 1-20 Hz.

Uso (a partir de experimentos/exp02_ispt_2014):
  python scripts/plot_glitch_hhe.py
Saida: results/evento_dia164_1503.png
"""
import numpy as np                               # contas
import obspy                                     # dados sismicos
import matplotlib                                # graficos
matplotlib.use("Agg")                            # desenha sem abrir janela
import matplotlib.pyplot as plt                  # graficos
from obspy import UTCDateTime                    # datas/horas

B = r"D:\Downloads\ISPT_DATA_SEISMO\2014\EC\ISPT\{c}.D\EC.ISPT..{c}.D.2014.164"   # arquivos do dia 164
TRECHOS = [(UTCDateTime("2014-06-13T15:02:50"), "15:03 (fora do catalogo)"),       # (inicio, titulo)
           (UTCDateTime("2014-06-13T18:10:20"), "18:10 M4.6 14 km (IG-EPN)")]

fig, ax = plt.subplots(6, 1, figsize=(11, 11))   # 2 trechos x 3 componentes
for j, (t0, titulo) in enumerate(TRECHOS):       # para cada trecho...
    for i, c in enumerate(["HHE", "HHN", "HHZ"]):   # ...e cada componente
        tr = obspy.read(B.format(c=c), starttime=t0, endtime=t0 + 120)[0]   # le 120 s
        d = tr.data.astype(float)                # HHE: contagens brutas
        if c != "HHE":                           # N e Z: tira media, suaviza bordas e filtra
            tr2 = tr.copy(); tr2.detrend("demean"); tr2.taper(0.05)
            tr2.filter("bandpass", freqmin=1, freqmax=20); d = tr2.data
        a = ax[j * 3 + i]                        # painel
        a.plot(np.arange(len(d)) / tr.stats.sampling_rate, d, lw=0.5)   # tempo em segundos
        a.set_ylabel(c); a.set_title(titulo if i == 0 else "", fontsize=9)
        print(titulo, c, "min %d max %d contagens" % (tr.data.min(), tr.data.max()))
ax[-1].set_xlabel("segundos desde o inicio do trecho")
plt.tight_layout()
plt.savefig("results/evento_dia164_1503.png", dpi=90)   # salva
