"""Plota os maiores disparos do STA/LTA de um dia nos 3 componentes.

Serve para ver, com os proprios olhos, se os disparos sao terremotos (onda P e depois S)
ou ruido (pulsos curtos sem S).

Uso: python plot_disparos_stalta.py <dia_juliano> <saida.png> [n_disparos]
Ex.: python scripts/plot_disparos_stalta.py 191 results/disparos_stalta_dia191.png 6
"""
import sys
import obspy, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from obspy.signal.trigger import classic_sta_lta, trigger_onset

B = r"D:\Downloads\ISPT_DATA_SEISMO\2014\EC\ISPT\{c}.D\EC.ISPT..{c}.D.2014.{d:03d}"
SENS = 1.6794e9  # contagens por m/s (epoca 2014b)

d, out = int(sys.argv[1]), sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
st0 = obspy.Stream()
for c in ["HHE", "HHN", "HHZ"]:
    st0 += obspy.read(B.format(c=c, d=d))
st0.merge(fill_value=0); st0.sort(keys=["channel"])
z = st0.select(component="Z")[0]; fs = z.stats.sampling_rate
f = z.copy(); f.detrend("demean"); f.filter("bandpass", freqmin=2, freqmax=15)
cft = classic_sta_lta(f.data, int(0.5 * fs), int(10 * fs))
on = trigger_onset(cft, 4.0, 1.5)
pico = np.array([cft[a:b + 1].max() for a, b in on])
dur = (on[:, 1] - on[:, 0]) / fs
print("disparos: %d | duracao mediana %.1f s | com pico >= 6: %d, >= 10: %d, >= 20: %d"
      % (len(on), np.median(dur), (pico >= 6).sum(), (pico >= 10).sum(), (pico >= 20).sum()))
print("disparos por hora:", np.bincount(((on[:, 0] / fs) // 3600).astype(int), minlength=24).tolist())

fig, ax = plt.subplots(n, 3, figsize=(15, 2.2 * n), sharex=True)
for i, k in enumerate(np.argsort(pico)[::-1][:n]):
    t = z.stats.starttime + on[k, 0] / fs
    s = st0.slice(t - 10, t + 20).copy(); s.detrend("demean"); s.filter("bandpass", freqmin=2, freqmax=15)
    for j, tr in enumerate(s):
        x = np.arange(tr.stats.npts) / tr.stats.sampling_rate - 10
        ax[i, j].plot(x, tr.data / SENS * 1e6, "k", lw=0.5); ax[i, j].axvline(0, color="r", lw=0.6)
        if i == 0: ax[i, j].set_title(tr.stats.channel)
        if j == 0: ax[i, j].set_ylabel(str(t)[11:19] + "\nµm/s")
for a in ax[-1]:
    a.set_xlabel("s (0 = disparo STA/LTA)")
fig.suptitle("ISPT %s: os %d maiores disparos STA/LTA (2-15 Hz)" % (z.stats.starttime.date, n))
plt.tight_layout(); plt.savefig(out, dpi=80)
print("figura:", out)
