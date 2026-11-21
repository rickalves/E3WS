# -*- coding: utf-8 -*-
"""PASSO D7b / Fase 2 - Rodar o E3WS em dias inteiros de dados continuos da ISPT.

Para cada dia (um dia por processo, varios dias em paralelo):
  1. le os 3 componentes do dia inteiro (+ 2 min do dia seguinte, para as ultimas janelas);
  2. DETECTOR: calcula as features de todas as janelas de 10 s, andando de 1 em 1 s (86.400 por dia),
     e chama o detector da ISPT de uma vez so (em lote, bem mais rapido);
  3. salva a probabilidade de ruido, P e S de cada janela (prob_2014DDD.csv.gz). Com isso da para
     testar outros limiares depois sem recalcular nada;
  4. GATILHO: a mesma logica do real_time/E3WS_rt.py: dispara quando a media das 3 ultimas prob. de P
     passa do limiar; rearma quando a media das 5 ultimas prob. de ruido passa de 0,99;
  5. para cada deteccao: PICKER (instante da onda P) e FONTE (magnitude, distancia, profundidade,
     back-azimuth) com 3 s e com 46 s de onda P; salva em det_2014DDD.csv.
O limiar usado aqui e o mais baixo (padrao 0,80). Deteccoes com limiar mais alto (0,90, 0,95) sao
um subconjunto: basta filtrar pela coluna prob_p_media3 depois.

Tudo usa as funcoes do Pablo (pasta functions/), com a correcao de instrumento pelo StationXML.

Uso (a partir de experimentos/exp02_ispt_2014):
  python scripts/e3ws_dia.py <tabela_de_dias.csv> <pasta_saida> [processos] [limiar] [detector]
    detector = 3C (padrao: 140 features, 3 componentes) ou NZ (90 features, so N e Z; funciona com o
               HHE congelado; ver DIARIO item 10)
Exemplo:
  python scripts/e3ws_dia.py results/dias_validacao.csv results/validacao_NZ 13 0.80 NZ
A tabela precisa ter uma coluna "dia" (dia juliano de 2014). Dias ja processados sao pulados.
"""
import os                                        # pastas e arquivos
import sys                                       # argumentos e caminho de importacao
import time                                      # medir o tempo
import collections                               # deque: "fila" de tamanho fixo para o gatilho
import warnings                                  # silenciar avisos repetitivos
from concurrent.futures import ProcessPoolExecutor   # varios dias em paralelo
warnings.filterwarnings("ignore")                # esconde avisos (nao afetam o resultado)
import numpy as np                               # contas com vetores
import pandas as pd                              # tabelas
import joblib                                    # carregar os modelos
import obspy                                     # dados sismicos
from obspy import UTCDateTime, read_inventory    # datas/horas e StationXML

# --- Caminhos ---
EXP = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))   # pasta do experimento
REPO = os.path.abspath(os.path.join(EXP, "..", ".."))                 # raiz do repositorio
sys.path.insert(0, EXP)                          # para importar functions/ (versao do Pablo)
import functions.pb_utils_v16 as pb_utils        # noqa: E402  features (st_FV) e pb_getpoint
import functions.pick_func_v16 as pick_func      # noqa: E402  picker (PP_pick)
from functions.utils import pb_SAM               # noqa: E402,F401  necessario para abrir os modelos de fonte

B = r"D:\Downloads\ISPT_DATA_SEISMO\2014\EC\ISPT\{c}.D\EC.ISPT..{c}.D.2014.{d:03d}"   # arquivos diarios
MODELOS = os.path.join(REPO, "models")           # modelos do E3WS (picker e fonte)
DETS = {                                         # nossos detectores, por tipo
    "3C": os.path.join(EXP, "treino_DET", "saved_models", "DET_ISPT_Whole_XGB_10tp3.0to3.0each0.5f7_unbalanced_official_v16.joblib"),
    "NZ": os.path.join(EXP, "treino_DET", "saved_models", "DET_ISPT_NZ_Whole_XGB_10tp3.0to3.0each0.5f7_unbalanced_official_v16.joblib"),
}
NOMES = pd.read_csv(os.path.join(EXP, "treino_DET", "pb_index_SASPe_official_v16.csv")).feature.tolist()[:140]   # nomes das 140 features
COLUNAS_NZ = [i for i, n in enumerate(NOMES) if n.startswith(("N_", "Z_"))]   # posicoes das 90 features de N e Z
PICK = os.path.join(MODELOS, "PICK", "PICK_CLF_XGBdep4n6000bytree0.46level1.0node1.0_P0.5_NPS_eachpoint_spike_v16.joblib")
STA_LAT, STA_LON = -1.262263, -81.0748           # posicao da ISPT
JANELA, PASSO = 10, 1                            # janelas de 10 s, andando de 1 s (como o E3WS)
JANELA_PICK, MOV_TIME, PTRAIN = 8, 0.1, 0.5      # parametros do picker (iguais ao E3WS_rt.py)
TPS = (3, 46)                                    # segundos de onda P usados na estimativa de fonte
N_AMOSTRAS = JANELA * 125 + 1                    # amostras de uma janela a 125 Hz

_M = {}                                          # modelos carregados (um conjunto por processo)


def modelos(tipo_det="3C"):
    """Carrega detector (3C ou NZ), picker e modelos de fonte uma vez por processo."""
    if not _M:                                   # se ainda nao carregou...
        _M["DET"] = joblib.load(DETS[tipo_det])  # detector da ISPT do tipo pedido
        _M["COLS"] = COLUNAS_NZ if tipo_det == "NZ" else list(range(140))   # quais features ele usa
        _M["PICK"] = joblib.load(PICK)           # picker
        for tp in TPS:                           # para 3 s e 46 s de onda P...
            sufixo = "_StackingXGB_7tp%df45_v16.0.joblib" % tp
            _M["MAG", tp] = joblib.load(os.path.join(MODELOS, "MAG", "MAG_Whole" + sufixo))   # magnitude
            _M["DIS", tp] = joblib.load(os.path.join(MODELOS, "DIS", "DIS_Whole" + sufixo))   # distancia
            _M["DEP", tp] = joblib.load(os.path.join(MODELOS, "DEP", "DEP_Whole" + sufixo))   # profundidade
            _M["COS", tp] = joblib.load(os.path.join(MODELOS, "BAZ", "welloriented_BAZ_Cos_STEAD" + sufixo))   # cos do BAZ
            _M["SIN", tp] = joblib.load(os.path.join(MODELOS, "BAZ", "welloriented_BAZ_Sin_STEAD" + sufixo))   # sen do BAZ
        _M["INV"] = read_inventory(os.path.join(EXP, "pz", "pb_ISPT.xml"))   # StationXML
    return _M


def ler_dia(dia):
    """Le os 3 componentes do dia inteiro + os 2 primeiros minutos do dia seguinte."""
    t0 = UTCDateTime(year=2014, julday=dia)      # inicio do dia
    st = obspy.Stream()                          # Stream vazio
    for canal in ("HHE", "HHN", "HHZ"):          # para cada componente...
        st += obspy.read(B.format(c=canal, d=dia))   # ...o dia
        if dia < 365 and os.path.exists(B.format(c=canal, d=dia + 1)):   # ...e o comeco do dia seguinte
            st += obspy.read(B.format(c=canal, d=dia + 1), starttime=t0 + 86400, endtime=t0 + 86400 + 120)
    st.merge(method=1)                           # junta os pedacos; falhas ficam "mascaradas"
    st.sort(keys=["channel"])                    # ordem E, N, Z
    return st


def janela_boa(w):
    """Uma janela e boa se tem os 3 componentes, sem falha de dados e com o tamanho certo."""
    return len(w) == 3 and all(not np.ma.is_masked(tr.data) and len(tr.data) == N_AMOSTRAS for tr in w)


def caracterizar(st, fim_janela, M):
    """Picker + fonte para uma deteccao cuja janela termina em fim_janela."""
    st_pick = st.slice(fim_janela - JANELA_PICK, fim_janela).copy()   # ultimos 8 s da janela que disparou
    curva = pick_func.PP_pick(st_pick, MOV_TIME, True, M["INV"], M["PICK"], fmin=1.0, fmax=7.0)   # prob. de P a cada 0,1 s
    p = st_pick[0].stats.starttime + np.argmax(curva) * MOV_TIME + 4 - PTRAIN   # instante da onda P (regra do E3WS_rt)
    ev = {"P_AI": str(p), "pick_prob_max": round(float(np.max(curva)), 4)}      # guarda o pick
    for tp in TPS:                               # com 3 s e com 46 s de onda P...
        w = st.slice(p - 7, p + tp).copy()       # ...7 s antes e tp s depois da P
        if len(w) != 3 or any(np.ma.is_masked(tr.data) for tr in w):   # ...se falta dado, deixa em branco
            continue
        w.trim(max(tr.stats.starttime for tr in w), min(tr.stats.endtime for tr in w))   # mesmos limites nos 3
        fv = np.real([pb_utils.st_FV(w, True, pzfile=M["INV"], fmin=1.0, fmax=45.0)])   # features 1-45 Hz
        mag = M["MAG", tp].predict(fv)[0]        # magnitude
        dis = M["DIS", tp].predict(fv)[0]        # distancia epicentral (km)
        dep = M["DEP", tp].predict(fv)[0]        # profundidade (km)
        baz = np.degrees(np.arctan2(M["SIN", tp].predict(fv)[0], M["COS", tp].predict(fv)[0]))   # back-azimuth (graus)
        lat, lon = pb_utils.pb_getpoint(STA_LAT, STA_LON, dis, baz)   # posicao estimada do epicentro
        ev.update({"mag_%ds" % tp: round(float(mag), 3), "dis_%ds" % tp: round(float(dis), 1),
                   "dep_%ds" % tp: round(float(dep), 1), "baz_%ds" % tp: round(float(baz), 1),
                   "lat_%ds" % tp: round(lat, 4), "lon_%ds" % tp: round(lon, 4)})
    return ev


def processar_dia(args):
    """Roda o E3WS num dia inteiro. Devolve um resumo."""
    dia, pasta, limiar, tipo_det = args          # desempacota
    inicio_relogio = time.time()                 # cronometro
    M = modelos(tipo_det)                        # modelos
    st = ler_dia(dia)                            # dados
    t0 = UTCDateTime(year=2014, julday=dia)      # 00:00 do dia

    # --- 1. Features de todas as janelas do dia ---
    fims, feats, boas = [], [], []               # fim de cada janela, features, se a janela e boa
    for k in range(86400 // PASSO):              # para cada segundo do dia...
        a = t0 + k * PASSO                       # ...inicio da janela
        w = st.slice(a, a + JANELA)              # ...recorta (sem copiar: a st_FV copia por dentro)
        fims.append(a + JANELA)                  # ...guarda o fim da janela
        if janela_boa(w):                        # ...se a janela e boa,
            feats.append(np.real(pb_utils.st_FV(w, True, pzfile=M["INV"], fmin=1.0, fmax=7.0)))   # ...140 features
            boas.append(True)
        else:                                    # ...se nao (falha de dados),
            boas.append(False)                   # ...marca como ruim
    boas = np.array(boas)                        # vira vetor

    # --- 2. Detector em lote ---
    prob = np.full((len(boas), 3), np.nan)       # prob. N, P, S de cada janela (NaN nas ruins)
    if boas.any():                               # se ha alguma janela boa...
        prob[boas] = M["DET"].predict_proba(np.array(feats)[:, M["COLS"]])   # ...todas de uma vez (so as features do detector)
    pd.DataFrame({"fim_janela": [str(f) for f in fims], "prob_n": prob[:, 0].round(4),
                  "prob_p": prob[:, 1].round(4), "prob_s": prob[:, 2].round(4)}).to_csv(
        os.path.join(pasta, "prob_2014%03d.csv.gz" % dia), index=False)   # salva (compactado)

    # --- 3. Gatilho (mesma logica do real_time/E3WS_rt.py) ---
    fila_p = collections.deque(maxlen=5)         # ultimas 5 prob. de P
    fila_n = collections.deque(maxlen=5)         # ultimas 5 prob. de ruido
    disparado_antes = disparado = 0              # estado do gatilho na janela anterior e na atual
    deteccoes = []                               # lista de deteccoes
    for k in range(len(boas)):                   # percorre as janelas em ordem
        if not boas[k]:                          # falha de dados: zera tudo (como se reiniciasse)
            fila_p.clear(); fila_n.clear(); disparado_antes = disparado = 0
            continue
        fila_p.append(prob[k, 1]); fila_n.append(prob[k, 0])   # acrescenta as prob. atuais
        ultimas_p = list(fila_p)[::-1]           # da mais recente para a mais antiga
        if len(ultimas_p) >= 3 and np.mean(ultimas_p[:3]) >= limiar:   # media das 3 ultimas P >= limiar
            disparado = 1                        # -> dispara
        if disparado == 1 and np.mean(fila_n) >= 0.99:   # media das 5 ultimas de ruido >= 0,99
            disparado = 0                        # -> rearma (pronto para o proximo evento)
        if disparado_antes == 0 and disparado == 1:   # acabou de disparar: NOVA DETECCAO
            ev = caracterizar(st, fims[k], M)    # picker + fonte
            ev["det_fim_janela"] = str(fims[k])  # quando o gatilho disparou
            ev["prob_p_media3"] = round(float(np.mean(ultimas_p[:3])), 4)   # forca do disparo
            ev["hhe_congelado"] = bool(np.ptp(st.slice(fims[k] - JANELA, fims[k]).select(channel="HHE")[0].data) == 0)   # HHE parado?
            deteccoes.append(ev)
        disparado_antes = disparado              # guarda o estado para a proxima janela

    colunas = ["P_AI", "det_fim_janela", "prob_p_media3", "pick_prob_max", "hhe_congelado"] + \
        ["%s_%ds" % (k, tp) for tp in TPS for k in ("mag", "dis", "dep", "baz", "lat", "lon")]
    pd.DataFrame(deteccoes, columns=colunas).to_csv(os.path.join(pasta, "det_2014%03d.csv" % dia), index=False)   # salva
    return dia, int(boas.sum()), len(deteccoes), round((time.time() - inicio_relogio) / 60, 1)


if __name__ == "__main__":
    arq_dias, pasta = sys.argv[1], sys.argv[2]   # tabela de dias e pasta de saida
    processos = int(sys.argv[3]) if len(sys.argv) > 3 else 13   # dias ao mesmo tempo
    limiar = float(sys.argv[4]) if len(sys.argv) > 4 else 0.80  # limiar do gatilho
    tipo_det = sys.argv[5].upper() if len(sys.argv) > 5 else "3C"   # qual detector usar
    os.makedirs(pasta, exist_ok=True)            # cria a pasta de saida
    dias = pd.read_csv(arq_dias).dia.tolist()    # dias a processar
    dias = [d for d in dias if not os.path.exists(os.path.join(pasta, "det_2014%03d.csv" % d))]   # pula os prontos
    print("Dias a processar (%d): %s | limiar %.2f | detector %s" % (len(dias), dias, limiar, tipo_det), flush=True)
    with ProcessPoolExecutor(processos) as ex:   # um dia por processo
        for dia, n_boas, n_det, minutos in ex.map(processar_dia, [(d, pasta, limiar, tipo_det) for d in dias]):
            print("  dia %3d: %d janelas boas, %d deteccoes, %.1f min" % (dia, n_boas, n_det, minutos), flush=True)
