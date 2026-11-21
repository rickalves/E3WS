# -*- coding: utf-8 -*-
"""Investiga os "spikes" (picos) no canal HHE da ISPT enquanto ele esta congelado (jan-jul/2014).

O que o script faz, para um dia escolhido:
  1. le os 3 componentes do dia;
  2. no HHE, acha os instantes em que o valor muda (no canal congelado ele quase nunca muda);
  3. conta quantos spikes existem e quanto tempo cada um dura;
  4. desenha 30 s em volta dos primeiros spikes, nos 3 componentes, para vermos como sao.

Uso (a partir de experimentos/exp02_ispt_2014):
  python scripts/investigar_spikes_hhe.py 60 results/spikes_hhe_dia060.png
"""
import sys                                   # para ler os argumentos da linha de comando
import numpy as np                           # contas com vetores
import obspy                                 # leitura de dados sismicos (miniSEED)
import matplotlib                            # graficos
matplotlib.use("Agg")                        # gera a figura em arquivo, sem abrir janela
import matplotlib.pyplot as plt              # funcoes de desenho

# Caminho dos arquivos diarios; {c} = canal (HHE, HHN, HHZ) e {d} = dia juliano com 3 digitos
B = r"D:\Downloads\ISPT_DATA_SEISMO\2014\EC\ISPT\{c}.D\EC.ISPT..{c}.D.2014.{d:03d}"

dia = int(sys.argv[1])                       # 1o argumento: dia juliano (ex.: 60 = 1o de marco)
saida = sys.argv[2]                          # 2o argumento: nome da figura de saida

# --- 1. Ler os 3 componentes ---
st = obspy.Stream()                          # Stream vazio para juntar os canais
for canal in ["HHE", "HHN", "HHZ"]:          # para cada componente...
    st += obspy.read(B.format(c=canal, d=dia))   # ...le o arquivo do dia e acrescenta ao Stream
st.merge(fill_value=0)                       # junta os pedacos de cada canal num trace so (falhas = 0)
st.sort(keys=["channel"])                    # garante a ordem E, N, Z

e = st.select(channel="HHE")[0]              # o trace do componente leste
fs = e.stats.sampling_rate                   # taxa de amostragem (125 amostras por segundo)
x = e.data.astype(float)                     # os valores do HHE como numeros reais

# --- 2. Achar onde o HHE muda de valor ---
muda = np.flatnonzero(np.diff(x) != 0)       # posicoes em que uma amostra e diferente da anterior
print("HHE do dia %d: %d amostras, %d mudancas de valor" % (dia, len(x), len(muda)))
valores, contagem = np.unique(x, return_counts=True)   # quais valores aparecem e quantas vezes
ordem = np.argsort(contagem)[::-1][:5]       # os 5 valores mais frequentes
print("valores mais frequentes (valor: n. de amostras):",
      {int(valores[i]): int(contagem[i]) for i in ordem})

# --- 3. Agrupar mudancas proximas em "spikes" (mudancas a menos de 1 s uma da outra = mesmo spike) ---
spikes = []                                  # lista de (inicio, fim) de cada spike, em amostras
for m in muda:                               # para cada mudanca de valor...
    if spikes and m - spikes[-1][1] < fs:    # ...se esta a menos de 1 s do spike anterior,
        spikes[-1][1] = m + 1                # ...estica o spike anterior ate aqui
    else:                                    # ...senao,
        spikes.append([m, m + 1])            # ...comeca um spike novo
dur = np.array([(b - a) / fs for a, b in spikes])   # duracao de cada spike em segundos
amp = np.array([np.ptp(x[a:b + 1]) for a, b in spikes])  # tamanho (pico a pico) em contagens
print("spikes no HHE: %d | duracao mediana %.3f s | maior %.2f s" % (
    len(spikes), np.median(dur) if len(dur) else 0, dur.max() if len(dur) else 0))
if len(amp):                                 # se existe pelo menos um spike...
    print("amplitude pico a pico (contagens): mediana %.0f, maior %.0f" % (np.median(amp), amp.max()))
horas = [int(a / fs // 3600) for a, _ in spikes]   # em que hora do dia cada spike comeca
print("spikes por hora:", np.bincount(horas, minlength=24).tolist())

# --- 4. Desenhar os primeiros spikes nos 3 componentes ---
n = min(4, len(spikes))                      # desenha ate 4 spikes
if n == 0:                                   # se nao ha spike nenhum...
    sys.exit("Nenhum spike neste dia.")      # ...termina aqui
fig, ax = plt.subplots(n, 3, figsize=(15, 2.4 * n), squeeze=False)   # grade: n linhas x 3 componentes
for i in range(n):                           # para cada spike...
    t = e.stats.starttime + spikes[i][0] / fs      # ...instante em que ele comeca
    trecho = st.slice(t - 10, t + 20)        # ...pega 10 s antes e 20 s depois
    for j, tr in enumerate(trecho):          # ...para cada componente
        tempo = np.arange(tr.stats.npts) / fs - 10  # eixo do tempo, 0 = inicio do spike
        ax[i, j].plot(tempo, tr.data, "k", lw=0.6)  # desenha o sinal bruto (contagens)
        ax[i, j].axvline(0, color="r", lw=0.6)      # linha vermelha no inicio do spike
        if i == 0:                           # na primeira linha...
            ax[i, j].set_title(tr.stats.channel)    # ...escreve o nome do canal
        if j == 0:                           # na primeira coluna...
            ax[i, j].set_ylabel(str(t)[11:19] + "\ncontagens")   # ...escreve a hora
for a in ax[-1]:                             # na ultima linha...
    a.set_xlabel("s (0 = inicio do spike no HHE)")   # ...rotulo do eixo do tempo
fig.suptitle("ISPT dia %d: spikes no HHE congelado (sinal bruto)" % dia)
plt.tight_layout()                           # ajusta os espacos
plt.savefig(saida, dpi=80)                   # salva a figura
print("figura:", saida)
