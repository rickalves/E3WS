# -*- coding: utf-8 -*-
"""Gera o relatorio em Word (.docx) do treino e da validacao do detector da ISPT (2014).

Junta os resultados que ja estao em results/ (logs, CSVs e figuras) num documento para discutir
com o Pablo. Antes, rode scripts/figuras_relatorio.py (gera as figuras das matrizes e da tabela).

Uso (a partir de experimentos/exp02_ispt_2014):
  python scripts/gerar_relatorio_docx.py
Saida: RELATORIO_treino_validacao_ISPT2014.docx
Precisa de: pip install python-docx
"""
import re                                        # ler numeros dos logs
import pandas as pd                              # tabelas
from docx import Document                        # cria o documento Word
from docx.shared import Pt, Cm, RGBColor         # tamanhos e cores
from docx.enum.text import WD_ALIGN_PARAGRAPH    # alinhamento
from docx.enum.table import WD_TABLE_ALIGNMENT   # alinhamento das tabelas
from docx.oxml import OxmlElement                # elementos XML (sombreamento de celula)
from docx.oxml.ns import qn                      # nomes XML do Word

AZUL = "2A78D6"                                  # cor do cabecalho das tabelas
AZUL_CLARO = "CDE2FB"                            # cor de destaque (melhor resultado)
SAIDA = "RELATORIO_treino_validacao_ISPT2014.docx"   # arquivo gerado

# ---------------- Numeros lidos dos resultados ----------------
log3c = open("results/treino_DET_log.txt", encoding="utf-8", errors="ignore").read()   # log do treino 3C
lognz = open("results/treino_DET_NZ_log.txt", encoding="utf-8", errors="ignore").read()   # log do treino NZ
n_eq_jan, n_eq = re.search(r"Terremotos: (\d+) janelas de (\d+) terremotos", log3c).groups()   # janelas e terremotos
n_p, n_s = re.search(r"'S\+3.0': (\d+), 'P\+3.0': (\d+)", log3c).groups()[::-1]   # janelas P e S
n_ruido, n_dias = re.search(r"Ruido: (\d+) janelas em (\d+) dias", log3c).groups()   # janelas de ruido
n_nan = re.search(r"HHE congelado\): (\d+)", log3c).group(1)   # janelas de ruido com HHE congelado
t3c = re.search(r"tempo total ([\d.]+) min", log3c).group(1)   # tempo de treino 3C
tnz = re.search(r"tempo total ([\d.]+) min", lognz).group(1)   # tempo de treino NZ
cat = pd.read_csv("results/avaliacao_validacao/eventos_catalogo.csv")   # eventos IG-EPN da validacao
mil = lambda x: "{:,}".format(int(x)).replace(",", ".")   # 1234567 -> "1.234.567"
virg = lambda x, n=2: ("%.*f" % (n, x + 1e-9)).replace(".", ",")   # 0.5 -> "0,50" (+1e-9: 0,945 arredonda para 0,95)

# ---------------- Funcoes de formatacao ----------------
doc = Document()                                 # documento novo
sec = doc.sections[0]                            # unica secao
sec.page_width, sec.page_height = Cm(21), Cm(29.7)   # A4
for lado in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, lado, Cm(2.2))                  # margens de 2,2 cm
st = doc.styles["Normal"]                        # estilo do texto
st.font.name = "Arial"; st.font.size = Pt(11)    # Arial 11
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")   # garante Arial em todo o texto
st.paragraph_format.space_after = Pt(6)          # espaco depois de cada paragrafo
for nivel, tam in ((0, 20), (1, 15), (2, 12.5)): # titulos: tamanho por nivel
    h = doc.styles["Title" if nivel == 0 else "Heading %d" % nivel]
    h.font.name = "Arial"; h.font.size = Pt(tam); h.font.bold = True
    h.font.color.rgb = RGBColor(0x0B, 0x0B, 0x0B) if nivel != 1 else RGBColor(0x1C, 0x5C, 0xAB)
    h.element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")


def sombra(celula, cor):
    """Pinta o fundo de uma celula de tabela."""
    tc = celula._tc.get_or_add_tcPr()            # propriedades da celula
    s = OxmlElement("w:shd")                     # elemento de sombreamento
    s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), cor)
    tc.append(s)


def par(texto, negrito=False, italico=False, tam=None, alinha=None):
    """Paragrafo simples. Trechos entre **...** ficam em negrito."""
    p = doc.add_paragraph()                      # novo paragrafo
    for i, pedaco in enumerate(texto.split("**")):   # alterna normal/negrito a cada **
        r = p.add_run(pedaco); r.bold = negrito or (i % 2 == 1); r.italic = italico
        if tam: r.font.size = Pt(tam)
    if alinha: p.alignment = alinha
    return p


def item(texto):
    """Item de lista com marcador (aceita **negrito**)."""
    p = doc.add_paragraph(style="List Bullet")   # estilo de lista do Word
    for i, pedaco in enumerate(texto.split("**")):
        p.add_run(pedaco).bold = (i % 2 == 1)
    return p


def tabela(cab, linhas, larguras, destaque=()):
    """Tabela com cabecalho azul. destaque = lista de (linha, coluna) para pintar de azul claro."""
    t = doc.add_table(rows=1, cols=len(cab))     # cria com a linha de cabecalho
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for k, txt in enumerate(cab):                # cabecalho
        c = t.rows[0].cells[k]; c.text = ""; r = c.paragraphs[0].add_run(txt)
        r.bold = True; r.font.color.rgb = RGBColor(255, 255, 255); r.font.size = Pt(10)
        sombra(c, AZUL)
    for i, lin in enumerate(linhas):             # linhas de dados
        cel = t.add_row().cells
        for k, txt in enumerate(lin):
            cel[k].text = ""; r = cel[k].paragraphs[0].add_run(str(txt)); r.font.size = Pt(10)
            if k > 0: cel[k].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            if (i, k) in destaque: sombra(cel[k], AZUL_CLARO); r.bold = True
    for lin in t.rows:                           # larguras das colunas
        for k, c in enumerate(lin.cells):
            c.width = Cm(larguras[k])
    doc.add_paragraph()                          # espaco depois da tabela
    return t


def figura(arq, legenda, largura=16):
    """Insere uma imagem centralizada com legenda."""
    doc.add_picture(arq, width=Cm(largura))      # imagem
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    par(legenda, italico=True, tam=9, alinha=WD_ALIGN_PARAGRAPH.CENTER)


# ---------------- Conteudo ----------------
doc.add_heading("Detector E3WS para a estação ISPT (2014): treino e validação", level=0)
par("Experimento 02 · Isla de la Plata, Equador · com HHE (3C) × sem HHE (NZ) · 23/11/2026", italico=True, tam=10)

doc.add_heading("1. Resumo", level=1)
item("Treinamos dois detectores para a ISPT com o ruído do ano inteiro de 2014 (%s dias, ~%s mil janelas) "
     "e o atr_eq oficial: um com os 3 componentes (3C) e um só com N e Z (NZ)." % (n_dias, round(int(n_ruido) / 1000)))
item("No teste 90/10 os dois são quase perfeitos (0 de 90.000 janelas de ruído viraram P), mas esse teste é otimista.")
item("Na validação em 13 dias inteiros fora do treino, o **NZ achou 5 de 9 eventos IG-EPN** e o **3C só 2 de 9**. "
     "No 1º semestre (HHE congelado) o 3C não achou nenhum (0/5).")
item("Só 1 alarme falso em 13 dias (um glitch do HHE), igual nos dois.")
item("**Proposta: usar o detector NZ em 2014.**")
item("Problemas para discutir: o picker genérico não funciona na ISPT e o detector não enxerga microssismos (seção 6).")

doc.add_heading("2. Contexto: o canal HHE em 2014", level=1)
par("De 01/01 a 08/07/2014 o canal HHE da ISPT ficou congelado em −8.382.254 contagens (perto do limite de "
    "24 bits), com spikes ocasionais. Nas janelas congeladas, as 45 features do componente E saem NaN. "
    "Há também trechos curtos em que o canal volta a funcionar no 1º semestre.")

doc.add_heading("3. Treino", level=1)
doc.add_heading("3.1 Dados", level=2)
tabela(["Conjunto", "Origem", "Janelas"], [
    ["Terremotos (P e S)", "atr_eq oficial do E3WS (M ≥ 3), %s terremotos" % mil(n_eq),
     "%s (P %s, S %s)" % (mil(n_eq_jan), mil(n_p), mil(n_s))],
    ["Ruído", "%s dias de 2014, 2 por mês, sorteados; 13 com HHE congelado" % n_dias,
     "%s úteis (%s com HHE congelado)" % (mil(n_ruido), mil(n_nan))],
    ["Ruído usado no modelo final", "amostra do conjunto acima (baseline do Pablo)", "900.000"],
], [4.2, 7.6, 4.8])
item("Janelas de 10 s, passo de 1 s, dados reamostrados a 100 Hz, resposta removida com o StationXML (aceleração), filtro 1–7 Hz.")
item("Máscara de eventos no ruído: a do gen_catag (STA/LTA recursivo 60/240 s, ±60 s), que tirou só 0,5 % das janelas.")
item("Dias excluídos do ruído: com eventos IG-EPN a < 300 km, telessismos M ≥ 6,5 ou dados incompletos.")
doc.add_heading("3.2 Modelo", level=2)
par("StandardScaler + XGBoost (gpu_hist; 6.000 árvores, profundidade 4, taxa 0,05; demais hiperparâmetros do E3WS). "
    "3C: 140 features (E, N, Z + 5 cruzadas), %s min. NZ: 90 features (só N e Z), %s min (RTX 3050)."
    % (virg(float(t3c), 1), virg(float(tnz), 1)))

doc.add_heading("4. Resultados", level=1)
figura("results/fig_matrizes_confusao.png", "Figura 1. Em cima: teste 90/10 (janelas). Embaixo: validação em 13 dias "
       "inteiros (eventos). TN não é contado na validação (dias inteiros, ~1,1 milhão de janelas).", 15.5)
doc.add_heading("4.1 Teste 90/10", level=2)
par("10 % dos terremotos e 90.000 janelas de ruído ficaram fora do treino. Os dois modelos acertam ~99 % das janelas "
    "P e S e nenhuma janela de ruído vira P. O teste é **otimista**: o ruído do teste vem dos mesmos dias do treino.")
doc.add_heading("4.2 Validação em dias inteiros", level=2)
par("13 dias que não entraram no treino: 6 calmos (3 com HHE congelado) e 7 com eventos IG-EPN a < 200 km. "
    "Gatilho igual ao E3WS_rt.py (média de 3 prob. de P ≥ limiar; rearme com média de 5 prob. de ruído ≥ 0,99). "
    "Referência: catálogo IG-EPN da pasta do Pablo (só M ≥ ~3,5). Um evento é \"encontrado\" se a P do E3WS cai "
    "entre a origem − 5 s e a origem + dist/5,5 + 15 s.")
linhas, dest = [], []                            # tabela de eventos
for i, (_, e) in enumerate(cat.iterrows()):      # um evento por linha
    p3, pn = e["3C_prob"], e["NZ_prob"]          # prob. de P de cada detector
    a3, an = p3 >= 0.80, pn >= 0.80              # achado pelo 3C / pelo NZ?
    linhas.append([e.hora[:16], virg(e.mag, 1), "%d" % e.dist_km, "%d" % round(e.prof_km),
                   "congelado" if e.hhe_congelado else "normal",
                   ("sim (%s)" % virg(p3)) if a3 else "–", ("sim (%s)" % virg(pn)) if an else "–"])
    if an and not a3: dest.append((i, 6))        # destaca onde so o NZ achou
linhas.append(["Total", "", "", "", "", "%d/9" % (cat["3C_prob"] >= 0.8).sum(), "%d/9" % (cat["NZ_prob"] >= 0.8).sum()])
dest.append((len(linhas) - 1, 6))
tabela(["Evento IG-EPN (UTC)", "M", "Dist. km", "Prof. km", "HHE", "3C", "NZ"], linhas,
       [3.6, 1.1, 1.6, 1.6, 2.2, 2.6, 2.6], dest)
par("Tabela 1. Eventos do catálogo nos dias de validação e prob. de P (limiar 0,80). Perdidos pelos dois: "
    "eventos a > 100 km, dois deles profundos (49 e 63 km).", italico=True, tam=9)
figura("results/fig_tabela_comparativa.png", "Figura 2. Comparação dos dois detectores.", 15.5)
doc.add_heading("4.3 Detecções fora do catálogo e alarme falso", level=2)
item("Dias calmos: 1 detecção em 6 dias (14/07 23:46:56), nos dois detectores. P e S nítidas, S−P ≈ 2,3 s "
     "(~19 km), M3,0 pelo E3WS: microssismo real (Figura 3).")
item("NZ no dia 13/06: detecções às 18:40 e 18:45 (M ~3,7, 15–24 km) com cara de réplicas do M4,6 (ainda não conferidas).")
item("**Único alarme falso: 13/06 15:03:26, nos dois detectores.** É o instante em que o HHE volta a congelar "
     "(salto para −8,38 milhões de contagens) com um pulso simultâneo em N e Z: glitch do instrumento (Figura 4).")
figura("results/avaliacao_validacao/amostra_deteccoes_NZ.png", "Figura 3. Única detecção do NZ em dias calmos "
       "(1–20 Hz; 0 = P do E3WS).", 16)
figura("results/evento_dia164_1503.png", "Figura 4. Alarme falso das 15:03 (em cima) × M4,6 das 18:10 (embaixo), "
       "13/06/2014. HHE em contagens brutas; N e Z filtrados 1–20 Hz.", 13)
doc.add_heading("4.4 Parâmetros de fonte (46 s de P)", level=2)
achados = cat[cat.NZ_prob >= 0.8]                # eventos achados pelo NZ
tabela(["Evento", "M cat.", "M E3WS", "Dist. cat. (km)", "Dist. E3WS (km)"],
       [[e.hora[:16], virg(e.mag, 1), virg(e.NZ_mag46), "%d" % e.dist_km, "%d" % round(e.NZ_dis46)]
        for e in achados.itertuples()], [4.2, 2.2, 2.2, 3.4, 3.4])
par("Tabela 2. Magnitude a ±0,25 e distância razoável. O back-azimuth no 1º semestre não tem sentido (depende do E).",
    italico=True, tam=9)

doc.add_heading("5. Por que o detector com HHE falha", level=1)
par("No treino, todas as janelas com o E congelado (NaN) eram ruído; os terremotos do atr_eq têm os 3 componentes. "
    "O 3C aprendeu o atalho **\"E congelado ⇒ ruído\"**: no 1º semestre a prob. de P fica ≤ 0,001, até no M4,6 a 14 km "
    "da estação. Tirando o E (NZ), o atalho some, e no 2º semestre o NZ rende o mesmo que o 3C.")

doc.add_heading("6. Problemas encontrados (para discutir)", level=1)
doc.add_heading("6.1 O picker genérico não funciona na ISPT", level=2)
par("Teste com o PICK_CLF_..._v16 (StationXML, pb_inst=True, a mesma configuração do E3WS_Ecuador.py) nos 8 s "
    "que terminam na janela que disparou. Prob. máxima de P:")
tabela(["Caso", "HHE real", "E = cópia do N", "E congelado"], [
    ["05/09 20:50, M3,9, 64 km (HHE normal)", "0,003", "0,003", "0,977"],
    ["01/08 10:05, M3,9, 112 km (HHE normal)", "0,002", "0,001", "0,993"],
    ["13/06 18:10, M4,6, 14 km (E já congelado)", "0,990", "0,001", "0,990"],
], [7.6, 2.8, 3.2, 3.0])
par("Com dados reais, o picker dá ~0,001 até em terremotos claros. Só dá ~0,99 com o E congelado (features NaN), "
    "o que é artefato. A P vira o argmax de uma curva quase plana; mesmo assim M e distância ficaram razoáveis.")
doc.add_heading("6.2 Baixa sensibilidade para microssismos", level=2)
par("O gatilho não fica travado (a condição de rearme vale em 99–100 % das janelas). O detector simplesmente "
    "dá P ≈ 0 para eventos pequenos. Dia 195, maiores disparos do STA/LTA clássico (1.592 no dia):")
tabela(["Disparo", "Amplitude Z", "Prob. P (3C)", "Prob. P (NZ)"], [
    ["23:46:56", "13,8 µm/s", "0,998", "0,999"],
    ["15:24:17", "1,3 µm/s", "0,167", "0,098"],
    ["20:46:29", "2,3 µm/s", "0,041", "0,039"],
    ["outros 12", "0,2–0,7 µm/s", "≤ 0,08", "≤ 0,005"],
], [3.2, 3.6, 3.6, 3.6])
par("Causas prováveis: o atr_eq só tem terremotos M ≥ 3, e a máscara do gen_catag deixa os microssismos dentro do "
    "ruído, então o detector aprende que eles são ruído. O detector serve para eventos de ~M3 para cima, mas não "
    "para contar a microssismicidade da ilha.")

doc.add_heading("7. Questões para o Pablo", level=1)
item("Usar o NZ para 2014 (e o 3C para anos com o HHE bom)?")
item("Picker: ele funcionou na SALI? Treinar um picker para a ISPT ou usar um pick clássico (AIC/STA-LTA) dentro da janela?")
item("Sensibilidade: aceitar completude ~M3; retreinar com a máscara estrita (STA/LTA 0,5/10 s, que tira os "
     "microssismos do ruído); acrescentar eventos pequenos ao atr_eq; ou complementar com outro método?")
item("Dados: catálogo IG-EPN 2014 com todas as magnitudes (a cópia atual só tem M ≥ 3,5) e a série de taxa de momento do GNSS.")
par("Scripts, logs e o passo a passo para reproduzir: repositório rickalves/E3WS, branch experimentos, pasta "
    "experimentos/exp02_ispt_2014 (GUIA.md, seções D5–D7).", italico=True, tam=9)

doc.save(SAIDA)                                  # grava o arquivo
print("Relatorio salvo em", SAIDA)
