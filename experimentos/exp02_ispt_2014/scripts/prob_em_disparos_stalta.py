# -*- coding: utf-8 -*-
"""Quanto o detector "acredita" nos maiores disparos do STA/LTA de um dia?

Acha os N maiores disparos do STA/LTA classico no Z (2-15 Hz, 0,5 s / 10 s, limiar 4) e, para cada
um, mostra a maior prob. de P e de S que o detector deu as janelas que terminam entre 1 s e 15 s
depois do disparo (lidas do prob_2014DDD.csv.gz salvo pelo e3ws_dia.py). Tambem mostra a amplitude
maxima no Z (em micrometros por segundo), para ter ideia do tamanho do evento.

Uso (a partir de experimentos/exp02_ispt_2014):
  python scripts/prob_em_disparos_stalta.py <pasta_validacao> <dia> [N]
Exemplo:
  python scripts/prob_em_disparos_stalta.py results/validacao_NZ 195 15
"""
import os                                        # caminhos
import sys                                       # argumentos
import numpy as np                               # contas
import pandas as pd                              # tabelas
import obspy                                     # dados sismicos
from obspy import UTCDateTime                    # datas/horas
from obspy.signal.trigger import classic_sta_lta, trigger_onset   # STA/LTA

B = r"D:\Downloads\ISPT_DATA_SEISMO\2014\EC\ISPT\HHZ.D\EC.ISPT..HHZ.D.2014.{d:03d}"   # vertical do dia
SENS = 1.68e9                                    # contagens por m/s (aproximado; so para ordem de grandeza)

pasta, dia = sys.argv[1], int(sys.argv[2])       # argumentos
n = int(sys.argv[3]) if len(sys.argv) > 3 else 15   # quantos disparos mostrar

st = obspy.read(B.format(d=dia)); st.merge(fill_value=0); tr = st[0]   # le o Z do dia
fs = tr.stats.sampling_rate                      # amostras por segundo
f = tr.copy(); f.detrend("demean"); f.filter("bandpass", freqmin=2, freqmax=15)   # filtro 2-15 Hz
cft = classic_sta_lta(f.data, int(0.5 * fs), int(10 * fs))   # razao STA/LTA
on = trigger_onset(cft, 4.0, 1.5)               # disparos
pico = np.array([cft[a:b + 1].max() for a, b in on])          # forca de cada disparo
amp = np.array([np.abs(f.data[a:a + int(20 * fs)]).max() for a, _ in on]) / SENS * 1e6   # amplitude em µm/s nos 20 s seguintes

p = pd.read_csv(os.path.join(pasta, "prob_2014%03d.csv.gz" % dia))   # probabilidades do detector
t_fim = np.array([UTCDateTime(x).timestamp for x in p.fim_janela])  # fim de cada janela (em segundos)

print("dia %d: %d disparos do STA/LTA; os %d maiores:" % (dia, len(on), n))
print("  hora       pico_STA/LTA  amp_Z(µm/s)  max_P   max_S")
for i in np.argsort(pico)[::-1][:n]:             # do maior para o menor disparo
    t0 = tr.stats.starttime.timestamp + on[i, 0] / fs   # hora do disparo
    sel = (t_fim >= t0 + 1) & (t_fim <= t0 + 15)  # janelas que terminam de 1 a 15 s depois
    print("  %s  %6.1f        %7.2f     %.3f   %.3f" % (
        str(UTCDateTime(t0))[11:19], pico[i], amp[i], p.prob_p[sel].max(), p.prob_s[sel].max()))
