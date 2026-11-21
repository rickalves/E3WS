# -*- coding: utf-8 -*-
"""PASSO D5 - Calcular as features (atributos) de ruido da ISPT para treinar o detector.

Versao 2 (baseline do Pablo). Para cada dia de treino escolhido no passo D3:
  1. MASCARA: acha os eventos fortes do dia com o STA/LTA do Pablo (gen_catag.py):
     STA/LTA recursivo no Z, filtro 1-7 Hz, janelas de 60 s e 240 s, liga em 2,8 e desliga em 0,5.
     Cada evento curto (< 10 min) apaga o trecho de 60 s antes ate 60 s depois.
     Eventos pequenos e spikes NAO sao apagados: o detector deve aprender que sao ruido.
  2. JANELAS: recorta janelas de 10 s, andando de PASSO em PASSO segundos (padrao 2 s).
  3. FILTRO DE QUALIDADE: descarta janelas com falha de dados (gap) ou tamanho errado.
     Janelas com o HHE congelado sao MANTIDAS (diferente do script original do Pablo).
  4. FEATURES: calcula os 140 numeros de cada janela com a funcao st_FV do Pablo, que corrige o
     instrumento pelo StationXML e converte para aceleracao.
Cada linha do CSV de saida = 140 features + 'SASPe' + 'ISPT' + 0 (0 = ruido), igual ao formato do Pablo.

O trabalho e dividido em tarefas de 1 hora de dado, rodadas em paralelo. Cada hora pronta e salva
em <saida>/partes/ e pulada se o script for rodado de novo (da para interromper e retomar).

Uso (a partir de experimentos/exp02_ispt_2014):
  python scripts/features_ruido.py <dias_ruido.csv> <pasta_saida> [processos] [passo_s]
Exemplo:
  python scripts/features_ruido.py results/dias_ruido.csv treino_DET/atr_noise/ISPT 14 2
"""
import os                                        # pastas e arquivos
import sys                                       # argumentos da linha de comando
import csv                                       # gravar CSV
import warnings                                  # para silenciar avisos repetitivos da ObsPy
from concurrent.futures import ProcessPoolExecutor   # rodar varias tarefas em paralelo
warnings.filterwarnings("ignore")                # esconde avisos (nao afetam o resultado)
import numpy as np                               # contas com vetores
import pandas as pd                              # tabelas
import obspy                                     # leitura de dados sismicos
from obspy import UTCDateTime, read_inventory    # datas/horas e leitura do StationXML
from obspy.signal.trigger import recursive_sta_lta, trigger_onset   # STA/LTA e deteccao dos disparos

# Pasta do experimento (um nivel acima de scripts/) e importacao das funcoes do Pablo
EXP = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, EXP)                          # permite "import functions...." a partir da pasta do experimento
import functions.pb_utils_v16 as pb_utils        # noqa: E402  funcao st_FV (versao com StationXML)

# Caminho dos arquivos diarios; {c} = canal, {d} = dia juliano com 3 digitos
B = r"D:\Downloads\ISPT_DATA_SEISMO\2014\EC\ISPT\{c}.D\EC.ISPT..{c}.D.2014.{d:03d}"
JANELA = 10                                      # tamanho da janela em segundos (o detector usa 10 s)
FS = 125                                         # taxa de amostragem da ISPT em 2014 (amostras/s)
N_AMOSTRAS = JANELA * FS + 1                     # amostras esperadas numa janela de 10 s (1251)
MARGEM = 60                                      # segundos apagados antes e depois de cada evento forte
_INVENTARIO = {}                                 # guarda o StationXML ja lido (um por processo)


def inventario():
    """Le o StationXML da ISPT so uma vez por processo (e demorado ler toda hora)."""
    if "inv" not in _INVENTARIO:                 # se ainda nao foi lido...
        _INVENTARIO["inv"] = read_inventory(os.path.join(EXP, "pz", "pb_ISPT.xml"))   # ...le
    return _INVENTARIO["inv"]                    # devolve o inventario


def mascara_do_dia(dia):
    """Devolve a lista de trechos (inicio, fim) a apagar no dia: os eventos fortes (metodo do Pablo)."""
    st = obspy.read(B.format(c="HHZ", d=dia))    # le o componente vertical do dia
    st.merge(fill_value=0)                       # junta os pedacos num trace so
    tr = st[0]                                   # o trace
    fs = tr.stats.sampling_rate                  # amostras por segundo
    tr.detrend("demean")                         # tira a media
    tr.detrend("linear")                         # tira a tendencia linear
    tr.filter("bandpass", freqmin=1.0, freqmax=7.0)   # deixa so 1-7 Hz, como o detector
    cft = recursive_sta_lta(tr.data, int(60 * fs), int(240 * fs))   # razao STA/LTA (60 s / 240 s)
    disparos = trigger_onset(cft, 2.8, 0.5)      # liga quando passa de 2,8, desliga abaixo de 0,5
    trechos = []                                 # lista de trechos a apagar
    for liga, desliga in disparos:               # para cada disparo...
        t_on = tr.stats.starttime + liga / fs    # ...instante em que ligou
        t_off = tr.stats.starttime + desliga / fs   # ...instante em que desligou
        if t_off - t_on < 600:                   # ...so eventos com menos de 10 min (regra do Pablo)
            trechos.append((t_on - MARGEM, t_off + MARGEM))   # ...apaga com 60 s de margem
    return trechos                               # devolve os trechos


def uma_hora(tarefa):
    """Calcula as features de 1 hora de dado e grava num CSV. Devolve um resumo com contagens."""
    dia, hora, trechos, passo, arquivo_saida = tarefa   # desempacota a tarefa
    t1 = UTCDateTime(year=2014, julday=dia) + hora * 3600   # inicio da hora
    t2 = t1 + 3600                               # fim da hora
    st = obspy.Stream()                          # Stream vazio
    for canal in ("HHE", "HHN", "HHZ"):          # le os 3 componentes...
        st += obspy.read(B.format(c=canal, d=dia), starttime=t1 - 1, endtime=t2 + JANELA + 1)   # ...so a hora (+ folga)
    st.merge(method=1)                           # junta pedacos; onde falta dado fica "mascarado" (gap)
    st.sort(keys=["channel"])                    # ordem E, N, Z (a st_FV espera essa ordem)
    inicio = np.array([a.timestamp for a, _ in trechos])   # inicios dos trechos apagados (em segundos)
    fim = np.array([b.timestamp for _, b in trechos])      # fins dos trechos apagados
    linhas = []                                  # linhas do CSV
    n_total = n_mascara = n_ruim = 0             # contadores para o resumo
    inv = inventario()                           # StationXML
    for k in range(int(3600 / passo)):          # para cada janela da hora...
        a = t1 + k * passo                       # ...inicio da janela
        b = a + JANELA                           # ...fim da janela
        n_total += 1                             # ...conta a janela
        if np.any((inicio < b.timestamp) & (fim > a.timestamp)):   # ...se encosta num trecho apagado,
            n_mascara += 1                       # ...conta como mascarada
            continue                             # ...e pula
        w = st.slice(a, b).copy()                # ...recorta a janela nos 3 componentes
        ok = len(w) == 3 and all(                # ...a janela e boa se tem 3 componentes e, em cada um,
            not np.ma.is_masked(tr.data)         # ......nao tem falha de dados
            and len(tr.data) == N_AMOSTRAS       # ......e tem o numero certo de amostras
            for tr in w)
        if not ok:                               # ...se nao e boa,
            n_ruim += 1                          # ...conta como ruim
            continue                             # ...e pula
        fv = pb_utils.st_FV(w, True, pzfile=inv, fmin=1.0, fmax=7.0)   # ...calcula as 140 features (1-7 Hz)
        linhas.append(list(np.real(fv)) + ["SASPe", "ISPT", 0])         # ...+ as 3 colunas finais (0 = ruido)
    with open(arquivo_saida, "w", newline="") as f:   # grava a hora inteira de uma vez
        csv.writer(f).writerows(linhas)          # (se o script parar no meio, a hora e refeita depois)
    return dia, hora, n_total, n_mascara, n_ruim, len(linhas)   # resumo


if __name__ == "__main__":                       # este bloco so roda quando o script e chamado direto
    arq_dias = sys.argv[1]                       # tabela do passo D3
    pasta = sys.argv[2]                          # pasta de saida
    processos = int(sys.argv[3]) if len(sys.argv) > 3 else 14   # quantas tarefas ao mesmo tempo
    passo = int(sys.argv[4]) if len(sys.argv) > 4 else 2        # de quantos em quantos segundos andar
    os.makedirs(os.path.join(pasta, "partes"), exist_ok=True)   # cria as pastas de saida

    dias = pd.read_csv(arq_dias).query("uso == 'treino'").dia.tolist()   # so os dias de treino
    print("Dias de treino:", dias, flush=True)

    with ProcessPoolExecutor(processos) as ex:   # calcula a mascara de cada dia, em paralelo
        mascaras = dict(zip(dias, ex.map(mascara_do_dia, dias)))
    for d in dias:                               # mostra quantos eventos fortes cada dia tem
        print("  dia %3d: %d eventos fortes apagados" % (d, len(mascaras[d])))

    tarefas = []                                 # lista de horas a calcular
    for d in dias:                               # para cada dia...
        for h in range(24):                      # ...e cada hora
            arq = os.path.join(pasta, "partes", "ISPT_2014%03d_h%02d.csv" % (d, h))   # arquivo da hora
            if not os.path.exists(arq):          # ...se ainda nao foi feita,
                tarefas.append((d, h, mascaras[d], passo, arq))   # ...entra na lista
    print("Horas a calcular: %d (passo de %d s)" % (len(tarefas), passo), flush=True)

    resumo = []                                  # resumo de cada hora
    with ProcessPoolExecutor(processos) as ex:   # roda as horas em paralelo
        for i, r in enumerate(ex.map(uma_hora, tarefas)):   # conforme cada hora termina...
            resumo.append(r)                     # ...guarda o resumo
            if (i + 1) % 24 == 0:                # ...a cada 24 horas prontas, mostra o progresso
                print("  %d/%d horas prontas" % (i + 1, len(tarefas)), flush=True)

    total_linhas = 0                             # junta as horas num arquivo por dia (formato do Pablo)
    for d in dias:
        nome = os.path.join(pasta, "DET_10s_pb_slidding%ds_2014%03dto2014%03d_NOISE_ISPT_f7_goodtrim_v16.csv" % (passo, d, d))
        with open(nome, "w") as saida:           # arquivo do dia
            for h in range(24):                  # para cada hora...
                with open(os.path.join(pasta, "partes", "ISPT_2014%03d_h%02d.csv" % (d, h))) as parte:
                    texto = parte.read()         # ...le a hora
                    saida.write(texto)           # ...e copia para o arquivo do dia
                    total_linhas += texto.count("\n")   # ...contando as linhas

    if resumo:                                   # resumo desta execucao
        r = np.array([x[2:] for x in resumo])    # colunas: total, mascaradas, ruins, uteis
        print("Janelas: total %d | mascaradas %d (%.1f%%) | ruins %d | uteis %d" % (
            r[:, 0].sum(), r[:, 1].sum(), 100 * r[:, 1].sum() / r[:, 0].sum(), r[:, 2].sum(), r[:, 3].sum()))
    print("Linhas de ruido gravadas (todos os dias): %d" % total_linhas)
