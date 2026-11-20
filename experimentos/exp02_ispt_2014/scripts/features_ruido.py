"""Calcula as features de ruido da ISPT para treinar o detector (DET).

Equivale ao pb_FV_noise_Ecuador.py do Pablo, com duas diferencas:
  1. a mascara de eventos e automatica: STA/LTA classico no Z (2-15 Hz, 0,5 s / 10 s,
     liga 4, desliga 1,5); cada disparo apaga o trecho [inicio - 15 s, fim + 45 s].
     Na ISPT esses disparos sao, em boa parte, microssismos reais (P e S visiveis);
  2. roda em paralelo, uma hora de dado por tarefa.

Cada janela de 10 s (passo de 1 s) fora da mascara, com os 3 componentes nao constantes e
com o numero certo de amostras, vira uma linha: 140 features + 'SASPe' + 'ISPT' + 0 (ruido).
Mesmo formato dos arquivos atr/ISPT do Pablo.

Uso: python features_ruido.py <dias_ruido.csv> <pasta_saida> [procs]
"""
import os, sys, csv, warnings
from concurrent.futures import ProcessPoolExecutor
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, obspy
from obspy import UTCDateTime as U, read_inventory
from obspy.signal.trigger import classic_sta_lta, trigger_onset

EXP = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, EXP)
import functions.pb_utils_v16 as pb_utils  # noqa: E402  (versao do Pablo: remove_response com StationXML)

B = r"D:\Downloads\ISPT_DATA_SEISMO\2014\EC\ISPT\{c}.D\EC.ISPT..{c}.D.2014.{d:03d}"
W, PASSO, ANTES, DEPOIS = 10, 1, 15, 45
_INV = {}


def inv():
    if "x" not in _INV:
        _INV["x"] = read_inventory(os.path.join(EXP, "pz", "pb_ISPT.xml"))
    return _INV["x"]


def mascara_dia(d):
    st = obspy.read(B.format(c="HHZ", d=d)); st.merge(fill_value=0); tr = st[0]
    fs = tr.stats.sampling_rate
    f = tr.copy(); f.detrend("demean"); f.filter("bandpass", freqmin=2, freqmax=15)
    on = trigger_onset(classic_sta_lta(f.data, int(0.5 * fs), int(10 * fs)), 4.0, 1.5)
    t0 = tr.stats.starttime
    return [(t0 + a / fs - ANTES, t0 + b / fs + DEPOIS) for a, b in on]


def hora(args):
    d, h, mask, out = args
    t1 = U(year=2014, julday=d) + h * 3600
    t2 = t1 + 3600
    st = obspy.Stream()
    for c in ("HHE", "HHN", "HHZ"):
        st += obspy.read(B.format(c=c, d=d), starttime=t1 - 1, endtime=t2 + W + 1)
    st.merge(method=1)
    st.sort(keys=["channel"])
    ini = np.array([m[0].timestamp for m in mask]); fim = np.array([m[1].timestamp for m in mask])
    linhas, n_tot, n_mask, n_ruim = [], 0, 0, 0
    I = inv()
    for k in range(int(3600 / PASSO)):
        a = t1 + k * PASSO; b = a + W; n_tot += 1
        if np.any((ini < b.timestamp) & (fim > a.timestamp)):
            n_mask += 1; continue
        w = st.slice(a, b).copy()
        npts = int(W * 125) + 1
        if len(w) != 3 or any(np.ma.is_masked(tr.data) or len(tr.data) != npts
                              or np.abs(tr.data - tr.data.mean()).sum() == 0 for tr in w):
            n_ruim += 1; continue
        fv = pb_utils.st_FV(w, True, pzfile=I, fmin=1.0, fmax=7.0)
        linhas.append(list(np.real(fv)) + ["SASPe", "ISPT", 0])
    with open(out, "w", newline="") as fh:
        csv.writer(fh).writerows(linhas)
    return d, h, n_tot, n_mask, n_ruim, len(linhas)


if __name__ == "__main__":
    dias_csv, pasta = sys.argv[1], sys.argv[2]
    procs = int(sys.argv[3]) if len(sys.argv) > 3 else 14
    os.makedirs(os.path.join(pasta, "partes"), exist_ok=True)
    dias = pd.read_csv(dias_csv).query("uso == 'treino'").dia.tolist()
    with ProcessPoolExecutor(procs) as ex:
        masks = dict(zip(dias, ex.map(mascara_dia, dias)))
    jobs = []
    for d in dias:
        for h in range(24):
            out = os.path.join(pasta, "partes", "ISPT_2014%03d_h%02d.csv" % (d, h))
            if not os.path.exists(out):  # permite retomar
                jobs.append((d, h, masks[d], out))
    print("dias:", dias, "| tarefas (horas) a fazer:", len(jobs), flush=True)
    res = []
    with ProcessPoolExecutor(procs) as ex:
        for i, r in enumerate(ex.map(hora, jobs)):
            res.append(r)
            if i % 24 == 23:
                print("  %d/%d horas prontas" % (i + 1, len(jobs)), flush=True)
    # junta tudo num arquivo por dia (formato do Pablo)
    tot = 0
    for d in dias:
        partes = [os.path.join(pasta, "partes", "ISPT_2014%03d_h%02d.csv" % (d, h)) for h in range(24)]
        nome = os.path.join(pasta, "DET_10s_pb_slidding1s_2014%03dto2014%03d_NOISE_ISPT_f7_goodtrim_v16.csv" % (d, d))
        with open(nome, "w") as fo:
            for p in partes:
                with open(p) as fi:
                    txt = fi.read(); fo.write(txt); tot += txt.count("\n")
    if res:
        r = np.array([x[2:] for x in res])
        print("janelas: total %d | mascaradas (eventos) %d (%.0f%%) | ruins %d | ruido util %d"
              % (r[:, 0].sum(), r[:, 1].sum(), 100 * r[:, 1].sum() / r[:, 0].sum(), r[:, 2].sum(), r[:, 3].sum()))
    print("linhas de ruido gravadas (todos os dias):", tot)
