"""E3WS em dados continuos (modo offline) para a estacao EC.ISPT.

Reproduz a logica de real_time/E3WS_rt.py (janela de 10 s, passo de 1 s,
gatilho = media das 3 ultimas prob. P >= thr, rearme quando a media das 5
ultimas prob. de ruido >= 0.99, picker com janela de 8 s), mas:
  - le os arquivos diarios SDS da ISPT (125 Hz; o st_FV reamostra para 100 Hz);
  - processa em blocos (chunks) em paralelo;
  - como e offline, estima a fonte direto com tp segundos de onda P
    (por padrao 3 s, como no alerta, e 46 s, como na tese, cap. 4.4).

Uso:
  python e3ws_continuo.py --inicio 2014-06-13T17:00 --fim 2014-06-13T19:30 \
      --saida results/teste.csv [--procs 14] [--chunk 3600] [--thr 0.8]
"""
import argparse, collections, csv, glob, os, sys, time, warnings
from concurrent.futures import ProcessPoolExecutor

warnings.filterwarnings("ignore")
import numpy as np
import obspy
from obspy import UTCDateTime
import joblib

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "real_time"))
import functions.pb_utils_v16 as pb_utils  # noqa: E402
import functions.pick_func_v16 as pick_func  # noqa: E402
from functions.utils import pb_SAM  # noqa: E402,F401  (necessario para desserializar os modelos)

EXP = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DADOS = r"D:\Downloads\ISPT_DATA_SEISMO\2014\EC\ISPT"
STA, STA_LAT, STA_LON = "ISPT", -1.262263, -81.0748
TROCA_EPOCA = UTCDateTime("2014-07-08T18:32:00")
MODELS = os.path.join(REPO, "models")
DET_FILE = os.path.join(MODELS, "DET", "DET_SLRZ_Whole_XGB_10tp0.5to4.0each0.5f7_unbalanced_official_v16.joblib")
PICK_FILE = os.path.join(MODELS, "PICK", "PICK_CLF_XGBdep4n6000bytree0.46level1.0node1.0_P0.5_NPS_eachpoint_spike_v16.joblib")
W_SEC, STRIDE, W_PICK, MOV_TIME, PTRAIN = 10, 1, 8, 0.1, 0.5

_M = {}


def carregar_modelos(tps, det_file):
    if _M:
        return _M
    _M["DET"] = joblib.load(det_file)
    _M["PICK"] = joblib.load(PICK_FILE)
    for tp in tps:
        sfx = "_StackingXGB_7tp%df45_v16.0.joblib" % tp
        _M[("MAG", tp)] = joblib.load(os.path.join(MODELS, "MAG", "MAG_Whole" + sfx))
        _M[("DIS", tp)] = joblib.load(os.path.join(MODELS, "DIS", "DIS_Whole" + sfx))
        _M[("DEP", tp)] = joblib.load(os.path.join(MODELS, "DEP", "DEP_Whole" + sfx))
        _M[("COS", tp)] = joblib.load(os.path.join(MODELS, "BAZ", "welloriented_BAZ_Cos_STEAD" + sfx))
        _M[("SIN", tp)] = joblib.load(os.path.join(MODELS, "BAZ", "welloriented_BAZ_Sin_STEAD" + sfx))
    return _M


def pz_para(t):
    nome = "ISPT_HH_2014a.pz" if t < TROCA_EPOCA else "ISPT_HH_2014b.pz"
    return os.path.join(EXP, "pz", nome)


def ler(t1, t2):
    """Le E, N, Z entre t1 e t2 (pode cruzar a virada do dia)."""
    st = obspy.Stream()
    dias = sorted({(t1 + k * 86400).julday for k in range(int((t2 - t1) // 86400) + 2)
                   if t1 + k * 86400 <= t2} | {t2.julday})
    for ch in ("HHE", "HHN", "HHZ"):
        for d in dias:
            f = os.path.join(DADOS, ch + ".D", "EC.ISPT..%s.D.%d.%03d" % (ch, t1.year, d))
            if os.path.exists(f):
                st += obspy.read(f, starttime=t1, endtime=t2)
    st.merge(method=1)  # resolve sobreposicoes; gaps ficam mascarados
    return st


def processar_chunk(args):
    t1, t2, tps, thr, det_file, salvar_prob = args
    M = carregar_modelos(tps, det_file)
    tmax = max(tps)
    st_all = ler(t1 - 2, t2 + tmax + 10)
    eventos, probs = [], []
    if len(st_all) < 3:
        return eventos, probs, 0
    st_all.sort(keys=["channel"])  # E, N, Z
    pzfile = pz_para(t1)
    buf_p, buf_n = collections.deque(maxlen=5), collections.deque(maxlen=5)
    trig_past = trig = 0
    n_win = int((t2 - t1) / STRIDE)
    for k in range(n_win):
        a = t1 + k * STRIDE
        b = a + W_SEC
        win = st_all.slice(a, b).copy()
        if len(win) != 3 or any(np.ma.is_masked(tr.data) or tr.stats.npts < 1200 for tr in win):
            buf_p.clear(); buf_n.clear(); trig_past = trig = 0
            continue
        win.trim(max(tr.stats.starttime for tr in win), min(tr.stats.endtime for tr in win))
        fv = np.real([pb_utils.st_FV(win, True, pzfile=pzfile, fmin=1.0, fmax=7.0)])
        pn, pp, ps = M["DET"].predict_proba(fv)[0]
        if salvar_prob:
            probs.append((str(b), round(pn, 4), round(pp, 4), round(ps, 4)))
        buf_p.append(pp); buf_n.append(pn)
        bp = np.flip(np.array(buf_p)); bn = np.flip(np.array(buf_n))
        if len(bp) >= 3 and np.mean(bp[0:3]) >= thr:
            trig = 1
        if trig == 1 and np.mean(bn) >= 0.99:
            trig = 0
        if trig_past == 0 and trig == 1:
            ev = caracterizar(st_all, win, pzfile, tps, M)
            ev["prob_p_media3"] = round(float(np.mean(bp[0:3])), 4)
            eventos.append(ev)
        trig_past = trig
    return eventos, probs, n_win


def caracterizar(st_all, win, pzfile, tps, M):
    st_pick = win.copy().trim(win[0].stats.endtime - W_PICK, win[0].stats.endtime)
    pp_curve = pick_func.PP_pick(st_pick, MOV_TIME, True, pzfile, M["PICK"], fmin=1.0, fmax=7.0)
    p_date = st_pick[0].stats.starttime + np.argmax(pp_curve) * MOV_TIME + 4 - PTRAIN
    ev = {"P_AI_date": str(p_date), "pick_prob_max": round(float(np.max(pp_curve)), 4),
          "det_janela_fim": str(win[0].stats.endtime)}
    for tp in tps:
        st_reg = st_all.slice(p_date - 7, p_date + tp).copy()
        ok = len(st_reg) == 3 and not any(np.ma.is_masked(tr.data) for tr in st_reg)
        if not ok:
            for k in ("mag", "dis", "dep", "baz", "lat", "lon"):
                ev["%s_%ds" % (k, tp)] = ""
            continue
        st_reg.trim(max(tr.stats.starttime for tr in st_reg), min(tr.stats.endtime for tr in st_reg))
        fv = np.real([pb_utils.st_FV(st_reg, True, pzfile=pzfile, fmin=1.0, fmax=45.0)])
        mag = M[("MAG", tp)].predict(fv)[0]
        dis = M[("DIS", tp)].predict(fv)[0]
        dep = M[("DEP", tp)].predict(fv)[0]
        baz = np.degrees(np.arctan2(M[("SIN", tp)].predict(fv)[0], M[("COS", tp)].predict(fv)[0]))
        lat, lon = pb_utils.pb_getpoint(STA_LAT, STA_LON, dis, baz)
        ev.update({"mag_%ds" % tp: round(float(mag), 3), "dis_%ds" % tp: round(float(dis), 1),
                   "dep_%ds" % tp: round(float(dep), 1), "baz_%ds" % tp: round(float(baz), 1),
                   "lat_%ds" % tp: round(lat, 4), "lon_%ds" % tp: round(lon, 4)})
    return ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inicio", required=True)
    ap.add_argument("--fim", required=True)
    ap.add_argument("--saida", required=True)
    ap.add_argument("--procs", type=int, default=14)
    ap.add_argument("--chunk", type=int, default=3600)
    ap.add_argument("--thr", type=float, default=0.80)
    ap.add_argument("--tps", default="3,46")
    ap.add_argument("--det", default=DET_FILE)
    ap.add_argument("--prob", action="store_true", help="salva prob. de cada janela")
    a = ap.parse_args()
    tps = [int(x) for x in a.tps.split(",")]
    t0, tf = UTCDateTime(a.inicio), UTCDateTime(a.fim)
    jobs, t = [], t0
    while t < tf:
        jobs.append((t, min(t + a.chunk, tf), tps, a.thr, a.det, a.prob))
        t += a.chunk
    ini = time.time()
    eventos, probs, n_tot = [], [], 0
    with ProcessPoolExecutor(min(a.procs, len(jobs))) as ex:
        for ev, pr, n in ex.map(processar_chunk, jobs):
            eventos += ev; probs += pr; n_tot += n
    dt = time.time() - ini
    os.makedirs(os.path.dirname(os.path.abspath(a.saida)), exist_ok=True)
    cols = ["P_AI_date", "det_janela_fim", "prob_p_media3", "pick_prob_max"] + \
        ["%s_%ds" % (k, tp) for tp in tps for k in ("mag", "dis", "dep", "baz", "lat", "lon")]
    with open(a.saida, "w", newline="") as fh:
        w = csv.DictWriter(fh, cols); w.writeheader(); w.writerows(eventos)
    if a.prob:
        with open(a.saida.replace(".csv", "_prob.csv"), "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["janela_fim", "prob_n", "prob_p", "prob_s"]); w.writerows(probs)
    horas = (tf - t0) / 3600
    print("Janelas: %d | deteccoes: %d | tempo: %.1f s | %.1f s por hora de dado | estimativa 1 ano: %.1f h"
          % (n_tot, len(eventos), dt, dt / horas, dt / horas * 8760 / 3600))


if __name__ == "__main__":
    main()
