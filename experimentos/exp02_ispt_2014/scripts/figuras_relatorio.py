# -*- coding: utf-8 -*-
"""Gera duas imagens para enviar ao Pablo: matrizes de confusao e tabela comparativa (3C x NZ).

Le tudo dos arquivos de resultado (nada de numero digitado a mao, exceto o alarme falso conferido
a olho no sismograma):
  - results/treino_DET_log.txt e treino_DET_NZ_log.txt -> matriz do teste 90/10 (janelas)
  - results/avaliacao_validacao/eventos_catalogo.csv   -> eventos IG-EPN achados ou nao
  - results/validacao_{3C,NZ}/det_*.csv                -> todas as deteccoes nos 13 dias

Uso (a partir de experimentos/exp02_ispt_2014):
  python scripts/figuras_relatorio.py
Saidas: results/fig_matrizes_confusao.png e results/fig_tabela_comparativa.png
"""
import glob                                      # listar arquivos
import re                                        # ler numeros do log
import numpy as np                               # contas
import pandas as pd                              # tabelas
import matplotlib                                # graficos
matplotlib.use("Agg")                            # desenha sem abrir janela
import matplotlib.pyplot as plt                  # graficos
from matplotlib.colors import LinearSegmentedColormap   # escala de cor
from obspy import UTCDateTime                    # datas/horas

LIMIAR = 0.80                                    # limiar do gatilho usado na validacao
GLITCH = ["2014-06-13T15:03"]                    # alarmes falsos conferidos no sismograma (DIARIO 13)
DET = {"3C": "Com HHE (3C)", "NZ": "Sem HHE (NZ)"}   # nomes bonitos dos detectores
LOG = {"3C": "results/treino_DET_log.txt", "NZ": "results/treino_DET_NZ_log.txt"}   # logs do treino

# Cores (paleta de referencia: rampa azul de um tom so; tinta e fundo neutros)
FUNDO, TINTA, TINTA2, CINZA = "#fcfcfb", "#0b0b0b", "#52514e", "#f0efec"
AZUL = LinearSegmentedColormap.from_list("azul", ["#f3f8fe", "#cde2fb", "#86b6ef", "#2a78d6", "#0d366b"])
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": TINTA, "axes.labelcolor": TINTA2,
                     "xtick.color": TINTA2, "ytick.color": TINTA2, "figure.facecolor": FUNDO})


def matriz_do_log(arq):
    """Le a matriz 3x3 (ruido/P/S) impressa no log do treino."""
    txt = open(arq, encoding="utf-8", errors="ignore").read()   # texto do log
    bloco = txt.split("Matriz de confusao")[1]   # parte depois do titulo da matriz
    nums = [int(x) for x in re.findall(r"\d+", bloco.split("precision")[0].split("\n", 1)[1])]   # 9 numeros
    return np.array(nums[:9]).reshape(3, 3)      # matriz 3x3


def deteccoes(tipo):
    """Junta as deteccoes dos 13 dias de um detector."""
    return pd.concat([pd.read_csv(f) for f in sorted(glob.glob("results/validacao_%s/det_*.csv" % tipo))])


cat = pd.read_csv("results/avaliacao_validacao/eventos_catalogo.csv")   # eventos IG-EPN (< 200 km)
cat["t"] = [UTCDateTime(h) for h in cat.hora]    # hora de origem como UTCDateTime
cat["congelado"] = cat.hhe_congelado.astype(bool)   # HHE congelado no dia do evento?

R = {}                                           # resultados por detector
for tipo in DET:                                 # para cada detector...
    acha = cat["%s_prob" % tipo] >= LIMIAR       # ...eventos do catalogo encontrados
    d = deteccoes(tipo)                          # ...todas as deteccoes
    t_p = [UTCDateTime(x) for x in d.P_AI]       # ...hora da P de cada deteccao
    no_cat = [any(c.t - 5 <= t <= c.t + c.dist_km / 5.5 + 15 for c in cat.itertuples()) for t in t_p]   # casou com o catalogo?
    falso = [any(str(t).startswith(g) for g in GLITCH) for t in t_p]   # e um alarme falso conferido?
    fora = sum(1 for a, b in zip(no_cat, falso) if not a and not b)    # fora do catalogo, mas nao e falso
    erro_mag = (cat["%s_mag46" % tipo] - cat.mag)[acha].abs().mean()   # erro medio de magnitude (46 s)
    R[tipo] = dict(M=matriz_do_log(LOG[tipo]), tp=int(acha.sum()), fn=int((~acha).sum()),
                   fp=int(sum(falso)), fora=fora, n_det=len(d),
                   sem1=(int(acha[cat.congelado].sum()), int(cat.congelado.sum())),
                   sem2=(int(acha[~cat.congelado].sum()), int((~cat.congelado).sum())),
                   l90=int((cat["%s_prob" % tipo] >= 0.90).sum()), l95=int((cat["%s_prob" % tipo] >= 0.95).sum()),
                   erro_mag=erro_mag)

# ---------------- Figura 1: matrizes de confusao ----------------
fig, ax = plt.subplots(2, 2, figsize=(10, 9.6), gridspec_kw={"height_ratios": [1.25, 1]})
for j, tipo in enumerate(DET):                   # uma coluna por detector
    # Linha 1: teste 90/10, janela a janela, 3 classes
    M = R[tipo]["M"]                             # matriz de contagens
    frac = M / M.sum(axis=1, keepdims=True)      # fracao por linha (recall de cada classe)
    a = ax[0, j]                                 # painel
    a.imshow(frac, cmap=AZUL, vmin=0, vmax=1)    # cor = fracao da linha
    for (i, k), v in np.ndenumerate(M):          # escreve contagem e % em cada celula
        cor = "white" if frac[i, k] > 0.6 else TINTA   # texto branco em celula escura
        a.text(k, i, "{:,}".format(v).replace(",", ".") + "\n" + ("%.1f%%" % (100 * frac[i, k])).replace(".", ","),
               ha="center", va="center", color=cor, fontsize=10)   # (ponto separa milhar)
    a.set_xticks(range(3)); a.set_xticklabels(["Ruido", "P", "S"])
    a.set_yticks(range(3)); a.set_yticklabels(["Ruido", "P", "S"])
    a.set_xlabel("Previsto"); a.set_ylabel("Verdadeiro")
    a.set_title("%s\nTeste 90/10 (janelas de 10 s)" % DET[tipo], fontsize=11, color=TINTA)
    # Linha 2: validacao em 13 dias inteiros, por evento
    r = R[tipo]                                  # numeros deste detector
    a = ax[1, j]                                 # painel
    V = np.array([[r["tp"], r["fn"]], [r["fp"], np.nan]])   # TN nao se conta (dias inteiros)
    fr = np.array([[r["tp"] / 9, r["fn"] / 9], [0.15, np.nan]])   # cor: fracao dos 9 eventos; FP claro
    a.imshow(np.ma.masked_invalid(fr), cmap=AZUL, vmin=0, vmax=1)   # celula TN fica sem cor
    a.add_patch(plt.Rectangle((0.5, 0.5), 1, 1, color=CINZA))   # fundo cinza na celula TN
    rot = [["%d de 9\n(%d%%)" % (r["tp"], round(100 * r["tp"] / 9)), "%d de 9\n(%d%%)" % (r["fn"], round(100 * r["fn"] / 9))],
           ["%d\n(glitch do HHE)" % r["fp"], "~1,1 milhao\nde janelas"]]   # textos das celulas
    for (i, k), s in np.ndenumerate(np.array(rot)):   # escreve os textos
        cor = "white" if (i == 0 and fr[i, k] > 0.6) else TINTA
        a.text(k, i, s, ha="center", va="center", color=cor, fontsize=10)
    a.set_xticks(range(2)); a.set_xticklabels(["Detectado", "Nao detectado"])
    a.set_yticks(range(2)); a.set_yticklabels(["Evento\nIG-EPN", "Sem\nevento"])
    a.set_title("Validacao: 13 dias inteiros (limiar %.2f)" % LIMIAR, fontsize=11, color=TINTA)
    a.text(0.5, -0.17, "+ %d deteccoes fora do catalogo (M < 3,5, provaveis reais)" % r["fora"],
           transform=a.transAxes, ha="center", fontsize=9, color=TINTA2)
fig.suptitle("ISPT 2014: detector com HHE x sem HHE", fontsize=14, fontweight="bold")
fig.text(0.5, 0.005, "Teste 90/10 otimista (ruido dos mesmos dias do treino). Validacao: 9 eventos IG-EPN "
         "a < 200 km (catalogo so M >= 3,5).", ha="center", fontsize=8.5, color=TINTA2)
plt.tight_layout(rect=(0, 0.02, 1, 0.97))
plt.savefig("results/fig_matrizes_confusao.png", dpi=150)   # salva
plt.close(fig)

# ---------------- Figura 2: tabela comparativa ----------------
pct = lambda m, c: ("%.1f%%" % (100 * m[c, c] / m[c].sum())).replace(".", ",")   # recall de uma classe (diagonal / linha)
linhas = [                                       # (metrica, 3C, NZ, qual e melhor: "3C", "NZ" ou "")
    ("Features", "140 (E, N, Z)", "90 (N, Z)", ""),
    ("Teste 90/10: acerto em P (janelas)", pct(R["3C"]["M"], 1), pct(R["NZ"]["M"], 1), ""),
    ("Teste 90/10: ruido que virou P", "%d de %s" % (R["3C"]["M"][0, 1], "{:,}".format(R["3C"]["M"][0].sum()).replace(",", ".")),
     "%d de %s" % (R["NZ"]["M"][0, 1], "{:,}".format(R["NZ"]["M"][0].sum()).replace(",", ".")), ""),
    ("Eventos IG-EPN achados (lim. 0,80)", "%d/9" % R["3C"]["tp"], "%d/9" % R["NZ"]["tp"], "NZ"),
    ("   1o semestre (HHE congelado)", "%d/%d" % R["3C"]["sem1"], "%d/%d" % R["NZ"]["sem1"], "NZ"),
    ("   2o semestre (HHE normal)", "%d/%d" % R["3C"]["sem2"], "%d/%d" % R["NZ"]["sem2"], ""),
    ("Eventos achados (lim. 0,90 / 0,95)", "%d/9  /  %d/9" % (R["3C"]["l90"], R["3C"]["l95"]),
     "%d/9  /  %d/9" % (R["NZ"]["l90"], R["NZ"]["l95"]), "NZ"),
    ("Alarmes falsos em 13 dias", "%d (glitch HHE)" % R["3C"]["fp"], "%d (o mesmo)" % R["NZ"]["fp"], ""),
    ("Deteccoes fora do catalogo", str(R["3C"]["fora"]), str(R["NZ"]["fora"]), ""),
    ("Erro medio de magnitude (46 s)", ("%.2f (%d ev.)" % (R["3C"]["erro_mag"], R["3C"]["tp"])).replace(".", ",", 1),
     ("%.2f (%d ev.)" % (R["NZ"]["erro_mag"], R["NZ"]["tp"])).replace(".", ",", 1), ""),
    ("Microssismos (< 2 um/s)", "nao detecta", "nao detecta", ""),
    ("Picker PICK v16 na ISPT", "nao funciona", "nao funciona", ""),
]
fig, a = plt.subplots(figsize=(9.5, 0.4 * (len(linhas) + 1) + 0.5))   # altura conforme o numero de linhas
a.axis("off")                                    # tabela sem eixos
tab = a.table(cellText=[l[:3] for l in linhas], colLabels=["", DET["3C"], DET["NZ"]],
              colWidths=[0.46, 0.27, 0.27], bbox=[0, 0, 1, 1], cellLoc="center")   # tabela ocupa o painel todo
tab.auto_set_font_size(False); tab.set_fontsize(10.5)   # tamanho da letra
for (i, k), c in tab.get_celld().items():        # estilo de cada celula
    c.set_edgecolor("#e2e1dc"); c.set_linewidth(0.6)   # linhas finas
    c.set_facecolor(FUNDO if i % 2 else "#f5f4f0")      # listras leves
    if k == 0:                                   # coluna das metricas: alinhada a esquerda
        c.set_text_props(ha="left", color=TINTA2); c.PAD = 0.03
    if i == 0:                                   # cabecalho
        c.set_facecolor("#2a78d6"); c.set_text_props(color="white", fontweight="bold")
    elif k > 0 and linhas[i - 1][3] == list(DET)[k - 1]:   # destaca o melhor
        c.set_facecolor("#cde2fb"); c.set_text_props(fontweight="bold")
a.set_title("ISPT 2014: detector com HHE x sem HHE", fontsize=12.5, fontweight="bold", pad=8)
fig.text(0.5, 0.005, "Eventos: 9 do IG-EPN a < 200 km em 13 dias de validacao (fora do treino). "
         "Destaque = melhor.", ha="center", fontsize=8.5, color=TINTA2)
plt.tight_layout()
plt.savefig("results/fig_tabela_comparativa.png", dpi=150, bbox_inches="tight")   # salva
print("Figuras salvas em results/fig_matrizes_confusao.png e results/fig_tabela_comparativa.png")
print({t: {k: v for k, v in r.items() if k != "M"} for t, r in R.items()})   # numeros usados
