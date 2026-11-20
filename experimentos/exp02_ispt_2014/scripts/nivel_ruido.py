"""Nivel de ruido (aceleracao, 1-7 Hz) da ISPT ao longo de 2014, por componente.

Mostra que o HHE da 0 (canal morto) ate 08/07/2014 e compara com o ruido da SLRZ
(estacao de exemplo do repositorio, acelerometro em Lima).

Uso (a partir de experimentos/exp02_ispt_2014):
  python scripts/nivel_ruido.py
"""
import os
import obspy, numpy as np
from obspy import UTCDateTime as U, read_inventory
from obspy.io.sac.sacpz import attach_paz

EXP = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(EXP, "..", ".."))
B = r"D:\Downloads\ISPT_DATA_SEISMO\2014\EC\ISPT\{c}.D\EC.ISPT..{c}.D.2014.{d:03d}"


def rms(st):
    return [float(np.sqrt(np.mean(tr.data[5000:-5000] ** 2))) for tr in st]


def slrz():
    """Ruido da SLRZ, com a mesma correcao (PZ) usada no real_time/E3WS_rt.py."""
    s = obspy.read(os.path.join(REPO, "real_time", "data", "Canta_M5.6_20220107", "SLRZ.HNZ.PE.2022.007.mseed"))
    t0 = s[0].stats.starttime
    # so os 10 s iniciais: o arquivo comeca poucos segundos antes do M5,6 de Canta
    s = s.slice(t0 + 1, t0 + 11).copy(); s.detrend("demean"); s.taper(0.05)
    s.filter("bandpass", freqmin=1, freqmax=7, zerophase=True); s.resample(100)
    for tr in s:
        attach_paz(tr, os.path.join(REPO, "real_time", "pz", "SLRZ_HN.pz"), todisp=False, torad=False)
        z = np.array(tr.stats.paz.zeros); z = np.delete(z, np.argwhere(z == 0)[0:2])
        tr.simulate(paz_remove={"gain": tr.stats.paz.gain, "poles": np.array(tr.stats.paz.poles), "sensitivity": 1, "zeros": z})
    s.filter("bandpass", freqmin=1, freqmax=7, zerophase=True)
    return float(np.sqrt(np.mean(s[0].data[100:-100] ** 2)))


if __name__ == "__main__":
    print("SLRZ (Lima, acelerometro), ruido Z: %.1e m/s2\n" % slrz())
    inv = read_inventory(os.path.join(EXP, "pz", "pb_ISPT.xml"))
    print("ISPT  dia  data        | RMS aceleracao 1-7 Hz (m/s2)  E / N / Z")
    for d in [15, 60, 120, 160, 185, 188, 190, 195, 230, 280, 330]:
        t = U(year=2014, julday=d, hour=3)
        st = obspy.Stream()
        for c in ["HHE", "HHN", "HHZ"]:
            st += obspy.read(B.format(c=c, d=d), starttime=t, endtime=t + 600)
        st.merge(fill_value=0); st.detrend("demean"); st.taper(0.05)
        st.remove_response(inventory=inv, output="ACC", pre_filt=[0.5, 1, 30, 40])
        st.filter("bandpass", freqmin=1, freqmax=7, zerophase=True)
        print("     %3d  %s  | %.1e / %.1e / %.1e" % (d, t.date, *rms(st)))
