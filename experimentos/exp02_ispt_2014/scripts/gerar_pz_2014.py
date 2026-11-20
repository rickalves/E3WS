"""Gera um SAC PZ de bloco unico para EC.ISPT.00.HH? em 2014.

O pb_ISPT.pz original tem 96 blocos (varios canais e epocas). O attach_paz da
ObsPy le o arquivo em sequencia, entao a resposta aplicada seria a do ultimo
bloco lido (outra epoca/sensor). Aqui selecionamos so a epoca certa.

2014 tem duas epocas (troca em 2014-07-08 18:30), mesmo sensor Guralp CMG3-ESPC,
com ganho diferente < 1 %. Geramos um arquivo por epoca.

Uso: python gerar_pz_2014.py <ISPT.xml> <pasta_saida>
"""
import sys, os
from obspy import read_inventory, UTCDateTime

xml, out = sys.argv[1], sys.argv[2]
inv = read_inventory(xml)
for nome, t in [("ISPT_HH_2014a", "2014-03-01"), ("ISPT_HH_2014b", "2014-10-01")]:
    sel = inv.select(station="ISPT", location="00", channel="HHZ", time=UTCDateTime(t))
    ch = sel[0][0][0]
    f = os.path.join(out, nome + ".pz")
    sel.write(f, format="SACPZ")
    print(f, ch.start_date, "->", ch.end_date, "sens=%.4e" % ch.response.instrument_sensitivity.value)
