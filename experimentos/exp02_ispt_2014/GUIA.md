# Guia passo a passo: E3WS na estação ISPT (2014)

Este guia reproduz, na ordem, tudo o que foi feito no experimento 02. Cada passo explica
**por que** é feito, o **comando**, o que **entra**, o que **sai** e o que você deve **ver**.
Os conceitos (onda P, STA/LTA, catálogo etc.) estão explicados em [CONCEITOS.md](CONCEITOS.md).
As descobertas e a ordem em que apareceram estão em [DIARIO.md](DIARIO.md).

**Convenções**
- Comandos para o **Anaconda Prompt** do Windows, já com o ambiente ativo:
  ```
  conda activate E3WS
  cd /d d:\Development\e3ws\experimentos\exp02_ispt_2014
  ```
  Todos os comandos abaixo partem dessa pasta.
- Caminhos de dados fixos nos scripts (mude no início do script se os dados estiverem em outro lugar):
  - dados da ISPT: `D:\Downloads\ISPT_DATA_SEISMO\2014\EC\ISPT\` (variável `B` ou `DADOS`);
  - material do Pablo: `D:\Downloads\E3WS_Ecuador\E3WS_Ecuador\` (só passado na linha de comando).
- Tempos medidos num PC com 16 núcleos e RTX 3050.

---

## Parte A: preparar o ambiente

### A1. Instalar o Miniconda e criar o ambiente
O E3WS foi feito para Python 3.7–3.9 com versões fixas das bibliotecas. Os modelos foram salvos
com `joblib` e só abrem corretamente com as mesmas versões de `xgboost` e `scikit-learn`.

```
winget install --id Anaconda.Miniconda3 -e
```
Depois, no **Anaconda Prompt**:
```
conda create -n E3WS --override-channels -c conda-forge python=3.9 pip
conda activate E3WS
pip install --only-binary=:all: --no-binary=python-speech-features numpy==1.22.4 scipy==1.8.1 xgboost==1.6.1 scikit-learn==1.1.1 obspy==1.3.0 python-speech-features==0.6 PyGeodesy==23.3.23 matplotlib==3.5.3 joblib pandas==1.5.3 gdown
```

**Se o pip der `CERTIFICATE_VERIFY_FAILED`:** é o antivírus (Kaspersky) interceptando o HTTPS.
A opção `--use-feature=truststore` **não funciona** com Python 3.9 (exige 3.10+). A solução é criar
um arquivo de certificados com a raiz do Kaspersky e apontar o pip do ambiente para ele, no PowerShell:
```powershell
$env_dir = "$env:USERPROFILE\miniconda3\envs\E3WS"; $py = "$env_dir\python.exe"
$root = Get-ChildItem Cert:\CurrentUser\Root, Cert:\LocalMachine\Root | ? Subject -like '*Kaspersky*' | Select -First 1
$pem = "-----BEGIN CERTIFICATE-----`n" + [Convert]::ToBase64String($root.RawData,'InsertLineBreaks') + "`n-----END CERTIFICATE-----`n"
$certifi = & $py -c "import pip._vendor.certifi as c;print(c.where())"
(Get-Content $certifi -Raw) + "`n" + $pem | Set-Content "$env_dir\ca-bundle-kaspersky.pem" -Encoding ascii
"[global]`ncert = $env_dir\ca-bundle-kaspersky.pem" | Set-Content "$env_dir\pip.ini" -Encoding ascii
```

**Verificação:** `python real_time\E3WS_rt.py` (a partir de `d:\Development\e3ws\real_time`) deve
reproduzir o experimento 01 (magnitude 5,34 com 3 s de onda P).

### A2. Baixar só os modelos necessários
O repositório completo tem 8,3 GB, quase tudo em modelos. Usamos *sparse checkout* para baixar
só os modelos que os scripts carregam: picker, detector de exemplo, fonte com 3–7 s e com 46 s.
```
git clone --filter=blob:none --no-checkout --depth 1 --branch experimentos https://github.com/rickalves/E3WS.git e3ws
cd e3ws
git sparse-checkout set --no-cone "/*" "!/models/*" "/models/PICK/*" "/models/DET/DET_SLRZ_*" "/models/MAG/*7tp[3-7]f45*" "/models/DIS/*7tp[3-7]f45*" "/models/DEP/*7tp[3-7]f45*" "/models/BAZ/*7tp3f45*"
git checkout experimentos
git sparse-checkout add "/models/MAG/*7tp46f45*" "/models/DIS/*7tp46f45*" "/models/DEP/*7tp46f45*" "/models/BAZ/*7tp46f45*"
```
`7tp46f45` = modelo que usa 7 s antes e 46 s depois da P, como a tese faz no modo "não tempo real" (seção 4.4).

---

## Parte B: conhecer os dados

### B1. Cobertura dos dados
**Por quê:** saber se há dias faltando, falhas, taxa de amostragem.
```
python scripts\inventario_dados.py "D:\Downloads\ISPT_DATA_SEISMO\2014\EC\ISPT" results\cobertura_dados_2014.csv
```
**Saída:** `results/cobertura_dados_2014.csv` (uma linha por arquivo diário).
**Esperado:** 365 dias × 3 canais, 125 Hz, location `00`; só os dias 189, 361 e 363 com < 23 h.
Os arquivos se chamam `EC.ISPT..HHZ.D.2014.DDD` (sem o `00` no nome, embora o cabeçalho tenha `00`).

### B2. Canais mortos
**Por quê:** um componente parado estraga as features de polarização do E3WS.
```
python scripts\canais_mortos.py results\canais_mortos_2014.csv
```
Conta quantos valores **diferentes** existem nas primeiras 200 mil amostras de cada dia. Sinal real
tem milhares; canal congelado tem 1.
**Esperado:** `HHE dias mortos: 183 (1, 189)`; HHN e HHZ: 0. **(~3 min)**

Confira você mesmo num dia (Python):
```python
import obspy, numpy as np
st = obspy.read(r"D:\Downloads\ISPT_DATA_SEISMO\2014\EC\ISPT\HHE.D\EC.ISPT..HHE.D.2014.060")
print(np.unique(st[0].data).size); st.plot()   # 1 valor, linha reta
```

### B3. Nível de ruído
**Por quê:** comparar a ISPT com a SLRZ (estação do exemplo do repositório) e ver o canal morto em aceleração.
```
python scripts\nivel_ruido.py > results\nivel_ruido.txt
```
**Esperado:** SLRZ ≈ 6,5×10⁻⁶ m/s²; ISPT ≈ 5×10⁻⁷ m/s² (14× mais silenciosa); HHE = 0 até o dia 188.

### B4. Catálogos de referência
**USGS** (global, só eventos maiores), direto da API pública:
```
curl -o results\catalogo_usgs_2014_r300km.csv "https://earthquake.usgs.gov/fdsnws/event/1/query?format=csv&starttime=2014-01-01&endtime=2015-01-01&latitude=-1.262263&longitude=-81.0748&maxradiuskm=300&orderby=time-asc"
curl -o results\usgs_mundo_M6.5_2014s2.csv "https://earthquake.usgs.gov/fdsnws/event/1/query?format=csv&starttime=2014-07-01&endtime=2015-01-01&minmagnitude=6.5&orderby=time-asc"
```
(No Windows, se o curl reclamar de certificado, acrescente `--ssl-no-revoke`.)

**IG-EPN** (rede do Equador): `D:\Downloads\E3WS_Ecuador\E3WS_Ecuador\old\Catalogo\pb_csv\cat_origen_2012_sep2023.txt`.
Esta cópia só tem M ≥ 3,5. As linhas de dados têm uma coluna a mais que o cabeçalho: leia com
`pd.read_csv(..., comment="#", skipinitialspace=True, index_col=False)`.

### B5. A rodada do Pablo na ISPT contra o IG-EPN
**Por quê:** ver o efeito do canal morto nas detecções.
```
python scripts\comparar_pablo_igepn.py "D:\Downloads\E3WS_Ecuador\E3WS_Ecuador\old\Catalogo\pb_csv\cat_origen_2012_sep2023.txt" "D:\Downloads\E3WS_Ecuador\E3WS_Ecuador\new\Figs\E3WS_ISPT.csv" > results\comparar_pablo_igepn.txt
```
**Esperado:** ~1000 detecções/mês até julho e ~30/mês depois; só 28 de 7135 do 1º semestre perto de
eventos do catálogo; o IG-EPN tem ~4 eventos/mês o ano todo.

---

## Parte C: teste do E3WS com o detector de outra estação (mostra por que treinar)

### C1. Arquivos de resposta (PZ) de 2014
**Por quê:** o E3WS do repositório corrige o instrumento com um arquivo SAC PZ de **um bloco**.
O `pb_ISPT.pz` do Drive tem 96 blocos e não serve direto.
```
python scripts\gerar_pz_2014.py "G:\Meu Drive\Mestrado\PPGEEC-UFC\dataset\ISPT_SEISMIC\pz\ISPT.xml" pz
```
**Saída:** `pz/ISPT_HH_2014a.pz` (até 08/07) e `pz/ISPT_HH_2014b.pz`.
(Mais adiante passamos a usar o StationXML direto, como o Pablo. Ver C3 e D3.)

### C2. Rodar o E3WS em 1,5 h em volta de um evento
```
python scripts\e3ws_continuo.py --inicio 2014-06-13T17:30 --fim 2014-06-13T19:00 --chunk 600 --saida results\teste_20140613.csv --prob
```
Usa o detector da **SLRZ**. **Esperado:** 94 % das janelas com prob. de P > 0,8, ou seja, o detector
acha que todo o ruído da ilha é terremoto. Isso prova que é preciso treinar um detector da ISPT.

### C3. Caracterizar o evento conhecido
```
python scripts\caracterizar_evento.py 2014-06-13T18:10:50 > results\caracterizar_evento_20140613.txt
```
**Esperado:** P em 18:10:49,0; com 46 s de onda P, distância 8 km (USGS: 11 km) e magnitude 5,2
(USGS: mb 4,4). Mostra que o picker e os modelos de fonte funcionam na ISPT.

---

## Parte D: treinar o detector (DET) da ISPT

Período: **2014-07-09 a 2014-12-31**, quando os 3 canais estão bons.

### D1. Funções e metadados do Pablo
**Por quê:** o Pablo calcula as features corrigindo o instrumento com o **StationXML**
(`remove_response`, que escolhe sozinho a época certa do sensor). Treino e uso do detector
precisam processar os dados exatamente do mesmo jeito.
```
mkdir functions
copy "D:\Downloads\E3WS_Ecuador\E3WS_Ecuador\functions\*.py" functions\
copy "D:\Downloads\E3WS_Ecuador\E3WS_Ecuador\old\pz\pb_ISPT.xml" pz\
mkdir treino_DET
copy "D:\Downloads\E3WS_Ecuador\E3WS_Ecuador\old\pb_index_SASPe_official_v16.csv" treino_DET\
copy "D:\Downloads\E3WS_Ecuador\E3WS_Ecuador\old\pb_index_DET_v16.csv" treino_DET\
```
(Já estão no repositório; só refaça se for começar do zero.)

### D2. Exemplos de terremotos (`atr_eq`)
**Por quê:** o detector precisa de exemplos de terremotos para aprender. Vêm de estações do
mundo todo, já resumidos em 140 números por janela.
```
mkdir treino_DET\atr_eq
cd treino_DET\atr_eq
python -c "import gdown; gdown.download(id='1_qY-1UVj-jOpQE3wkcrgzEYx8n4_J5sV', output='DET_7.00tp3.00_pb_Whole_mag3.0dis200.0dep100.0f7_withindex_PSlabel_goodtrim_v16.csv')"
cd ..\..
```
**Saída:** 549 MB, 167.525 linhas, 187 colunas. A pasta do Google Drive
(`1YkaV11K1OOwO61H2Q1kQd5GYRD_DABoq`) tem 8 arquivos (tp0.50 a tp4.00, ~4,1 GB). O Pablo usou só o tp3.00 no Equador.
Para listar os IDs: `python -c "import gdown; [print(f.id, f.path) for f in gdown.download_folder('https://drive.google.com/drive/folders/1YkaV11K1OOwO61H2Q1kQd5GYRD_DABoq', skip_download=True, quiet=True)]"`

### D3. Escolher os dias de ruído
**Por quê:** os dias de "ruído" ensinam ao detector como é o silêncio da ilha. Não podem ter terremotos.
```
python scripts\escolher_dias_ruido.py "D:\Downloads\E3WS_Ecuador\E3WS_Ecuador\old\Catalogo\pb_csv\cat_origen_2012_sep2023.txt" results\usgs_mundo_M6.5_2014s2.csv results\dias_ruido.csv 30 > results\dias_ruido_log.txt
```
Para cada dia de 9/jul a 31/dez: mede o ruído e conta disparos do STA/LTA; exclui dias com evento
IG-EPN a < 300 km (54 dias) ou telessismo M ≥ 6,5 (18 dias). Dos 110 candidatos, escolhe 30
espalhados no tempo (em cada bloco, o de menos disparos). **(~3 min)**
**Saída:** `results/dias_ruido.csv`, coluna `uso` = `treino` (30), `validacao` (80) ou `excluido`.

### D4. Ver o que são os disparos do STA/LTA
```
python scripts\plot_disparos_stalta.py 191 results\disparos_stalta_dia191.png 6
```
**Esperado:** ~1000 disparos no dia mais calmo; os maiores têm **onda P e depois S**, ou seja, são
microssismos reais. Por isso o passo seguinte apaga um trecho em volta de cada disparo.

### D5. Calcular as features de ruído
```
python scripts\features_ruido.py results\dias_ruido.csv treino_DET\atr_noise\ISPT 14
```
Para cada dia de treino: apaga [−15 s, +45 s] em volta de cada disparo do STA/LTA, recorta janelas
de 10 s andando de 1 s, descarta janelas com falha ou canal constante e calcula as 140 features.
O último número (`14`) é quantos processos usar; use menos se quiser usar o PC ao mesmo tempo.
**Pode ser interrompido e retomado:** cada hora pronta fica em `treino_DET/atr_noise/ISPT/partes/`
e é pulada na próxima execução. **(~1 h a 1,5 h com 14 processos)**
**Saída:** um CSV por dia, `DET_10s_pb_slidding1s_2014DDDto2014DDD_NOISE_ISPT_f7_goodtrim_v16.csv`,
143 colunas (140 features + `SASPe`, `ISPT`, `0`), mesmo formato dos arquivos do Pablo.

### D6. Treinar
```
python scripts\treinar_DET.py treino_DET
```
1. junta as janelas de terremotos (rótulos 1 = P, 2 = S) e até 900 mil de ruído (rótulo 0);
2. **teste**: treina com 90 % e avalia nos 10 % restantes (terremotos nunca vistos), mostrando a
   matriz de confusão e quantas janelas de ruído viram "P" com limiar 0,8 / 0,9 / 0,95;
3. treina o **modelo final** com tudo e salva
   `treino_DET/saved_models/DET_ISPT_Whole_XGB_10tp3.0to3.0each0.5f7_unbalanced_official_v16.joblib`.

Opções: `--cpu` (sem GPU), `--sem-teste` (pula o passo 2, metade do tempo).
Guarde a saída do terminal: `python scripts\treinar_DET.py treino_DET > results\treino_DET_log.txt`.

### D7. Validar (a fazer)
Rodar o E3WS com o detector novo nos dias de `validacao`: contar falsos alarmes por dia e ver
quantos eventos do IG-EPN são encontrados. Antes, o `e3ws_continuo.py` precisa passar a usar as
funções do Pablo (StationXML) e o detector da ISPT.

---

## Mapa dos arquivos

| Arquivo | O que é |
|---|---|
| `scripts/inventario_dados.py` | B1: cobertura diária |
| `scripts/canais_mortos.py` | B2: dias com canal congelado |
| `scripts/nivel_ruido.py` | B3: ruído em aceleração, ISPT × SLRZ |
| `scripts/comparar_pablo_igepn.py` | B5: rodada do Pablo × catálogo IG-EPN |
| `scripts/gerar_pz_2014.py` | C1: PZ de bloco único por época |
| `scripts/e3ws_continuo.py` | C2: E3WS em dados contínuos (versão de teste, com PZ) |
| `scripts/caracterizar_evento.py` | C3: picker + fonte num evento conhecido |
| `scripts/escolher_dias_ruido.py` | D3: dias de treino e de validação |
| `scripts/plot_disparos_stalta.py` | D4: figura dos maiores disparos |
| `scripts/features_ruido.py` | D5: features de ruído |
| `scripts/treinar_DET.py` | D6: treino do detector |
| `functions/` | funções do E3WS na versão do Pablo (StationXML) |
| `pz/` | `pb_ISPT.xml` (StationXML) e PZ de 2014 |
| `results/` | saídas pequenas (CSV, TXT, PNG) |
| `treino_DET/` | dados de treino (**fora do git**, grandes; refaça com D2 e D5) |
