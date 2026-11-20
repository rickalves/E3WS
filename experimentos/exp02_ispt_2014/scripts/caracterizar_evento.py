"""Caracteriza um evento conhecido com o picker e os modelos de fonte do E3WS.

Acha a chegada da P com um STA/LTA perto do horario dado, monta a janela do picker e
estima magnitude, distancia, profundidade e back-azimuth com 3 s e 46 s de onda P.
Tambem mede o custo de cada etapa (features e DET).

Uso: python caracterizar_evento.py <horario_aprox_UTC>
Ex.: python scripts/caracterizar_evento.py 2014-06-13T18:10:50   (USGS mb 4,4, 11 km da ISPT)
"""
import sys, os, time, __main__
import numpy as np
from obspy import UTCDateTime as U
from obspy.signal.trigger import classic_sta_lta, trigger_onset

sys.path.insert(0, os.path.dirname(__file__))
import e3ws_continuo as e  # noqa: E402
__main__.pb_SAM = e.pb_SAM  # necessario para desserializar os modelos

t_ev = U(sys.argv[1])
M = e.carregar_modelos([3, 46], e.DET_FILE)
st = e.ler(t_ev - 360, t_ev + 130); st.sort(keys=["channel"])
z = st.select(component="Z")[0].copy(); z.filter("bandpass", freqmin=2, freqmax=15)
fs = z.stats.sampling_rate
on = [z.stats.starttime + o[0] / fs for o in trigger_onset(classic_sta_lta(z.data, int(0.5 * fs), int(20 * fs)), 6, 2)]
print("Disparos STA/LTA no trecho:", [str(o)[11:22] for o in on])
tP = min(on, key=lambda o: abs(o - t_ev))
win = st.slice(tP + 4 - 10, tP + 4).copy()  # janela do picker: P perto do meio
ev = e.caracterizar(st, win, e.pz_para(tP), [3, 46], M)
for k, v in ev.items():
    print("  %-14s %s" % (k, v))

w = st.slice(t_ev - 300, t_ev - 290).copy()
t = time.time()
for _ in range(20):
    fv = np.real([e.pb_utils.st_FV(w, True, pzfile=e.pz_para(tP), fmin=1.0, fmax=7.0)])
t1 = (time.time() - t) / 20
t = time.time()
for _ in range(20):
    M["DET"].predict_proba(fv)
t2 = (time.time() - t) / 20
t = time.time(); M["DET"].predict_proba(np.repeat(fv, 1000, axis=0)); t3 = (time.time() - t) / 1000
print("Custo: features %.1f ms/janela | DET %.1f ms por chamada | DET em lote %.2f ms/janela" % (t1 * 1e3, t2 * 1e3, t3 * 1e3))
