# -*- coding: utf-8 -*-
"""O picker do E3WS funciona na ISPT? E o HHE atrapalha?

Para algumas deteccoes da validacao, roda o picker (PP_pick) nos 8 s que terminam no fim da janela
que disparou (igual ao e3ws_dia.py), em tres versoes dos dados:
  - original:      os 3 componentes como estao no arquivo;
  - E=copia de N:  o HHE trocado por uma copia do HHN (um E "saudavel", mas falso);
  - E congelado:   o HHE trocado por um valor constante (-8382254, como no 1o semestre).
Se o picker funcionasse, a probabilidade maxima de P seria alta (perto de 1) na versao original.

Uso (a partir de experimentos/exp02_ispt_2014):
  python scripts/testar_picker.py
"""
import os                                        # caminhos
import sys                                       # caminho de importacao
import warnings                                  # avisos
warnings.filterwarnings("ignore")                # esconde avisos do obspy/xgboost
EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # pasta do experimento
sys.path.insert(0, EXP)                          # para achar functions/
sys.path.insert(0, os.path.join(EXP, "scripts")) # para achar e3ws_dia.py
import numpy as np                               # contas
import __main__                                  # modulo principal
from functions.utils import pb_SAM               # classe usada dentro dos modelos salvos
__main__.pb_SAM = pb_SAM                         # o joblib procura pb_SAM no __main__
import e3ws_dia as E                             # reaproveita leitura de dados e modelos
from obspy import UTCDateTime                    # datas/horas
import functions.pick_func_v16 as pf             # picker (PP_pick)

M = E.modelos("NZ")                              # carrega modelos (o picker e o mesmo para 3C e NZ)
CASOS = [(248, "2014-09-05T20:50:49", "M3.9 64 km, HHE normal"),       # (dia, fim da janela, descricao)
         (213, "2014-08-01T10:05:54", "M3.9 112 km, HHE normal"),
         (164, "2014-06-13T15:03:29", "deteccao fora do catalogo"),
         (164, "2014-06-13T18:10:52", "M4.6 14 km, HHE congelado")]

for dia, fim, desc in CASOS:                     # para cada caso...
    st = E.ler_dia(dia)                          # ...le o dia inteiro (E, N, Z)
    fim = UTCDateTime(fim)                       # ...fim da janela que disparou
    base = st.slice(fim - 8, fim).copy()         # ...os 8 s que o picker analisa
    e = base.select(channel="HHE")[0].data       # ...dados do HHE
    print("\n%s (%s)  variacao HHE=%d contagens" % (fim, desc, np.ptp(e)))
    versoes = {"original": base}                 # versao 1: dados reais
    v2 = base.copy()                             # versao 2: E = copia de N
    v2.select(channel="HHE")[0].data = base.select(channel="HHN")[0].data.copy()
    versoes["E=copia de N"] = v2
    v3 = base.copy()                             # versao 3: E congelado (constante)
    v3.select(channel="HHE")[0].data = np.full_like(e, -8382254)
    versoes["E congelado"] = v3
    for nome, s in versoes.items():              # roda o picker em cada versao
        curva = pf.PP_pick(s, 0.1, True, M["INV"], M["PICK"], fmin=1.0, fmax=7.0)   # prob. de P a cada 0,1 s
        print("  %-14s prob. maxima de P = %.4f" % (nome, curva.max()))
