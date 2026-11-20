"""Escolhe os dias de ruido para treinar o detector (DET) da ISPT.

Para cada dia de 2014-07-09 (dia 190) a 2014-12-31 (dia 365):
  - nivel de ruido: RMS da velocidade no Z, 1-7 Hz (mediana das 24 horas);
  - n. de disparos de um STA/LTA classico (0,5 s / 10 s, 2-15 Hz, liga 4, desliga 1,5) no Z,
    um indicador de quantos eventos pequenos existem no dia;
  - exclusao: dia incompleto, evento IG-EPN a < 300 km da ISPT, telessismo M >= 6,5 (USGS)
    nesse dia ou nas ultimas 3 h do dia anterior.
Escolhe N dias de treino (padrao 20): divide o periodo em N blocos e pega, em cada bloco,
o dia candidato com menos disparos. Os demais candidatos ficam para validacao.
Obs.: os disparos do STA/LTA na ISPT sao, em boa parte, microssismos reais (P e S visiveis),
por isso o calculo das features de ruido mascara um trecho em volta de cada disparo.

Uso: python escolher_dias_ruido.py <catalogo_igepn_origen.txt> <usgs_mundo.csv> <saida.csv> [N]
"""
import sys, csv, os
import numpy as np, pandas as pd, obspy
from obspy import UTCDateTime as U
from obspy.signal.trigger import classic_sta_lta, trigger_onset
from obspy.geodetics import gps2dist_azimuth
from concurrent.futures import ProcessPoolExecutor

B = r"D:\Downloads\ISPT_DATA_SEISMO\2014\EC\ISPT\{c}.D\EC.ISPT..{c}.D.2014.{d:03d}"
SENS = 1.6794e9  # contagens por m/s (epoca 2014b, HHZ)
LAT, LON = -1.262263, -81.0748


def medir(d):
    st = obspy.read(B.format(c="HHZ", d=d))
    st.merge(fill_value=0)
    tr = st[0]
    horas = tr.stats.npts / tr.stats.sampling_rate / 3600
    fs = tr.stats.sampling_rate
    a = tr.copy(); a.detrend("demean"); a.filter("bandpass", freqmin=1, freqmax=7, zerophase=True)
    x = a.data / SENS
    n = int(3600 * fs)
    rms_h = [np.sqrt(np.mean(x[i:i + n] ** 2)) for i in range(0, len(x) - n + 1, n)]
    b = tr.copy(); b.detrend("demean"); b.filter("bandpass", freqmin=2, freqmax=15)
    cft = classic_sta_lta(b.data, int(0.5 * fs), int(10 * fs))
    trig = trigger_onset(cft, 4.0, 1.5)
    return {"dia": d, "data": str(U(year=2014, julday=d).date), "horas": round(horas, 2),
            "rms_z_ms": float(np.median(rms_h)), "n_stalta": len(trig)}


if __name__ == "__main__":
    cat_file, usgs_file, out = sys.argv[1:4]
    with ProcessPoolExecutor(12) as ex:
        R = pd.DataFrame(list(ex.map(medir, range(190, 366))))

    c = pd.read_csv(cat_file, comment="#", skipinitialspace=True, index_col=False)
    c.columns = [x.strip() for x in c.columns]
    c["t"] = pd.to_datetime(c["time_value"].str.strip())
    c = c[(c.t >= "2014-07-01") & (c.t < "2015-01-01")]
    c["dist"] = [gps2dist_azimuth(LAT, LON, a, b)[0] / 1e3 for a, b in zip(c.latitude_value, c.longitude_value)]
    dias_cat = set(c[c.dist < 300].t.dt.dayofyear)

    u = pd.read_csv(usgs_file)
    u["t"] = pd.to_datetime(u.time)
    dias_tele = set(u.t.dt.dayofyear) | set((u[u.t.dt.hour >= 21].t.dt.dayofyear + 1))

    R["evento_igepn"] = R.dia.isin(dias_cat)
    R["telessismo"] = R.dia.isin(dias_tele)
    R["candidato"] = (R.horas >= 23.9) & ~R.evento_igepn & ~R.telessismo

    cand = R[R.candidato].copy()
    n_treino = int(sys.argv[4]) if len(sys.argv) > 4 else 20
    blocos = np.array_split(cand.sort_values("dia"), n_treino)
    treino = [blk.sort_values("n_stalta").iloc[0].dia for blk in blocos]
    R["uso"] = np.where(R.dia.isin(treino), "treino", np.where(R.candidato, "validacao", "excluido"))
    R.to_csv(out, index=False)

    print("dias avaliados:", len(R), "| candidatos:", R.candidato.sum(),
          "| excluidos: incompleto %d, IG-EPN %d, telessismo %d" % ((R.horas < 23.9).sum(), R.evento_igepn.sum(), R.telessismo.sum()))
    print("ruido Z (m/s) em todos os dias: p10 %.2e | mediana %.2e | p90 %.2e" % tuple(np.percentile(R.rms_z_ms, [10, 50, 90])))
    print("disparos STA/LTA por dia: p10 %d | mediana %d | p90 %d" % tuple(np.percentile(R.n_stalta, [10, 50, 90])))
    print("\nDias de treino:")
    print(R[R.uso == "treino"][["dia", "data", "rms_z_ms", "n_stalta"]].to_string(index=False))
