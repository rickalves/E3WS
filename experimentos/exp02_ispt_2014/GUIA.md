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

**Versão 2 (baseline do Pablo, 2026-11-21):** ruído do **ano inteiro** de 2014, inclusive o 1º
semestre com o HHE congelado e com spikes (o detector precisa aprender que isso também é ruído),
**≥ 900 mil janelas** de ruído e a **máscara do Pablo**, que só apaga eventos fortes.
A versão 1 (só 2º semestre, máscara estrita, 462 mil janelas) está no histórico do git (commit
6ec2698) e os dados dela em `treino_DET/atr_noise/ISPT_v1_mascara_estrita/`. Ver o DIARIO, item 8.

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
**Por quê:** os dias de "ruído" ensinam ao detector como é o fundo da estação, inclusive os defeitos
do sensor (HHE congelado e spikes). Não podem ter terremotos grandes.
```
python scripts\escolher_dias_ruido.py results\cobertura_dados_2014.csv "D:\Downloads\E3WS_Ecuador\E3WS_Ecuador\old\Catalogo\pb_csv\cat_origen_2012_sep2023.txt" results\usgs_mundo_M6.5_2014.csv results\dias_ruido.csv 2 > results\dias_ruido_log.txt
```
Regras: dia completo nos 3 canais; fora o dia 189 (troca do sensor); fora dias com evento IG-EPN a
< 300 km (96 dias) ou telessismo M ≥ 6,5 (47 dias). Dos 213 candidatos, sorteia **2 por mês** (um por
quinzena, semente fixa 30002). **(segundos)**
**Esperado:** `Dias de treino: 24 (13 com HHE congelado, 11 com HHE normal)`.
**Saída:** `results/dias_ruido.csv`, coluna `uso` = `treino` (24), `validacao` (189) ou `excluido`.

### D4. Ver o que são os disparos e os spikes
```
python scripts\plot_disparos_stalta.py 191 results\disparos_stalta_dia191.png 6
python scripts\investigar_spikes_hhe.py 60 results\spikes_hhe_dia060.png
```
**Esperado:** no dia 191, os maiores disparos do STA/LTA curto são microssismos reais (P e depois S).
No dia 60, o HHE fica parado em −8.382.254 contagens (perto do limite do conversor, −8.388.608) e
tem alguns spikes de menos de 1 s; o HHZ também mostra pulsos curtos.

### D5. Calcular as features de ruído
```
python scripts\features_ruido.py results\dias_ruido.csv treino_DET\atr_noise\ISPT 14 2
```
Para cada dia de treino:
1. **máscara do Pablo**: STA/LTA recursivo no Z (1–7 Hz, 60 s/240 s, liga 2,8, desliga 0,5);
   cada evento com menos de 10 min apaga de 60 s antes a 60 s depois. Apaga ~1–10 % do dia.
   Eventos pequenos e spikes ficam: o detector aprende que são ruído;
2. janelas de 10 s andando de **2 s** (o `2` no fim do comando; o Pablo usa 1 s);
3. descarta só janelas com falha de dados ou tamanho errado. **Mantém** as janelas com o HHE
   congelado (o script original do Pablo descartava). Nelas, 10 das 140 features viram NaN
   (não dá para calcular, por exemplo, a entropia de um sinal constante). O XGBoost trata NaN
   como "valor ausente", e o mesmo acontece quando o detector roda nesses dias;
4. 140 features por janela com a `st_FV` do Pablo (StationXML).

O `14` é quantos processos usar; use menos se quiser usar o PC ao mesmo tempo.
**Pode ser interrompido e retomado:** cada hora pronta fica em `treino_DET/atr_noise/ISPT/partes/`
e é pulada na próxima execução. **(estimativa: 30–45 min)**
**Esperado (~35 min):** `Janelas: total 1036800 | mascaradas 5547 (0.5%) | ruins 1812 | uteis 1029441`.
Guarde o log: acrescente `> results\features_ruido_log.txt` ao comando.
**Saída:** um CSV por dia, `DET_10s_pb_slidding2s_2014DDDto2014DDD_NOISE_ISPT_f7_goodtrim_v16.csv`,
143 colunas (140 features + `SASPe`, `ISPT`, `0`), mesmo formato dos arquivos do Pablo.

### D6. Treinar
```
python scripts\treinar_DET.py treino_DET > results\treino_DET_log.txt
```
1. junta as janelas de terremotos (rótulos 1 = P, 2 = S) e sorteia **900 mil** de ruído (rótulo 0);
2. **teste**: treina com 90 % e avalia nos 10 % restantes (terremotos nunca vistos e ruído nunca
   visto). Mostra a matriz de confusão e quantas janelas de ruído viram "P" com limiar
   0,8 / 0,9 / 0,95, separando ruído com HHE congelado e normal;
3. treina o **modelo final** com tudo e salva
   `treino_DET/saved_models/DET_ISPT_Whole_XGB_10tp3.0to3.0each0.5f7_unbalanced_official_v16.joblib`.

Opções: `--cpu` (sem GPU), `--sem-teste` (pula o passo 2, metade do tempo), `--ruido N`
(quantas janelas de ruído; `--ruido 0` usa todas).
**Esperado (~23 min na RTX 3050):** no teste, ruído 90000/90000 correto; P com recall 0,99;
`P >= 0.80: acerta 98.4% das janelas P | ruido que vira P: 0.0000%`; modelo salvo com 4,3 MB.
Esses números são otimistas (o ruído de teste vem dos mesmos dias do treino); a avaliação real é o D7.

### D6b. Treinar o detector sem o HHE (só N e Z)
```
python scripts\treinar_DET.py treino_DET --componentes NZ > results\treino_DET_NZ_log.txt
```
Mesmo treino, só com as 90 features dos componentes N e Z. **Por quê:** o detector de 3 componentes
aprendeu o atalho "HHE congelado = ruído" e não detecta terremotos no 1º semestre (DIARIO item 10).
O Pablo pediu para testar as duas formas: com o HHE (3C) e sem o HHE (NZ). **(~11 min)**
**Saída:** `treino_DET/saved_models/DET_ISPT_NZ_..._v16.joblib`.

### D7. Validar os dois detectores

**Catálogo de referência.** Arquivo IG-EPN da pasta do Pablo:
`D:\Downloads\E3WS_Ecuador\E3WS_Ecuador\old\Catalogo\pb_csv\cat_origen_2012_sep2023.txt`.
- Tem 3.042 eventos no Equador inteiro, de jan/2012 a set/2023. Colunas usadas: hora de origem,
  latitude, longitude, profundidade e `magnitude_value_M`.
- **Só eventos maiores**: a menor magnitude é 3,1, e quase todos têm M ≥ 3,5. O catálogo completo do
  IG-EPN vai até ~M2 e foi pedido ao Pablo.
- Em 2014: 216 eventos no país, 53 a < 200 km da ISPT, 7 a < 50 km.
- Na mesma pasta, sem uso por enquanto: `cat_magnitud_*` (magnitudes por estação), `cat_picks_*`
  (chegadas das ondas por estação; a ISPT tem só 3 em 2014) e `CatalogoHomogenizado.txt`
  (Beauval et al., 2013).
- **Limitação:** este catálogo mede se o detector acha os eventos **maiores**. Ele **não** diz se as
  detecções pequenas são microssismos reais ou alarmes falsos; para isso, há as figuras do D7c.

O **USGS** só foi usado para o evento do teste C3 e para a lista de telessismos M ≥ 6,5 (passo D3).

**D7a. Escolher os dias de validação** (nenhum entrou no treino):
```
python scripts\escolher_dias_validacao.py results\dias_ruido.csv "D:\Downloads\E3WS_Ecuador\E3WS_Ecuador\old\Catalogo\pb_csv\cat_origen_2012_sep2023.txt" results\dias_validacao.csv 3
```
- Grupo A, "calmos": 3 por semestre, sorteados entre os dias de `validacao` do D3 (sem evento
  IG-EPN a < 300 km).
- Grupo B, "com eventos": os 3 dias de cada semestre com mais eventos IG-EPN a < 200 km, mais o dia
  164 (2014-06-13).

**Esperado:** 13 dias (6 do grupo A, 7 do grupo B), com **9 eventos** IG-EPN a < 200 km.

Para uma checagem rápida, só em volta desses eventos:
```
python scripts\prob_em_eventos.py "D:\...\cat_origen_2012_sep2023.txt" NZ 2 5 164 183 199 213 248
```
Troque `NZ` por `3C` para o outro detector.

**D7b. Rodar o E3WS nos dias inteiros**, um dia por processo:
```
python scripts\e3ws_dia.py results\dias_validacao.csv results\validacao_NZ 13 0.80 NZ > results\validacao_NZ_log.txt
python scripts\e3ws_dia.py results\dias_validacao.csv results\validacao_3C 13 0.80 3C > results\validacao_3C_log.txt
```
Para cada dia, o script salva `prob_2014DDD.csv.gz` (prob. de ruído/P/S de cada uma das 86.400
janelas) e `det_2014DDD.csv` (detecções com pick, magnitude, distância, profundidade e BAZ a 3 s e
a 46 s). O gatilho segue a lógica do `real_time/E3WS_rt.py`. O limiar 0,80 dá o conjunto mais
amplo; para 0,90 ou 0,95, basta filtrar a coluna `prob_p_media3`. **(~45–60 min por detector)**

**D7c. Avaliar:**
```
python scripts\avaliar_validacao.py results\dias_validacao.csv "D:\...\cat_origen_2012_sep2023.txt" results\avaliacao_validacao
```
- **"Encontrou o evento"** = existe uma detecção com a onda P entre 5 s antes da hora de origem e
  (distância ÷ 5,5 km/s) + 15 s depois.
- Mostra também: detecções por dia (limiares 0,80/0,90/0,95; HHE congelado × normal), a
  concordância entre os dois detectores e figuras de 12 detecções sorteadas dos dias calmos, para
  conferir a olho se são terremotos (P e depois S) ou ruído.

**Esperado (limiar 0,80):** 3C acha 2/9 eventos e NZ acha 5/9. O 3C dá 5 detecções e o NZ dá 10
(resultados completos no `RELATORIO_validacao.md`).

**D7d. Diagnósticos** (por que há poucas detecções; o picker; o alarme falso):
```
python scripts\analisar_probabilidades.py results\validacao_NZ results\dias_validacao.csv 0.80
python scripts\prob_em_disparos_stalta.py results\validacao_NZ 195 15
python scripts\testar_picker.py > results\testar_picker.txt
python scripts\plot_glitch_hhe.py
```
- `analisar_probabilidades.py`: por dia, quantas janelas têm P alta, quantos candidatos existem,
  quantas detecções saem com o rearme e quanto tempo o gatilho fica travado. Salva
  `analise_probabilidades.csv` na pasta. Troque `NZ` por `3C` para o outro detector.
- `prob_em_disparos_stalta.py`: a prob. de P/S que o detector dá aos maiores disparos do STA/LTA
  de um dia. **Esperado no dia 195:** só o disparo de 23:46:56 (13,8 µm/s) com P ≈ 1; os
  microssismos (≤ 2 µm/s) com P ≈ 0.
- `testar_picker.py`: o picker com o HHE real, com o E trocado pelo N e com o E congelado.
  **Esperado:** prob. ≈ 0,001 nas duas primeiras versões e ≈ 0,99 só com o E congelado (o picker
  não funciona na ISPT).
- `plot_glitch_hhe.py`: figura `results/evento_dia164_1503.png`, alarme falso × terremoto real.

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
| `scripts/investigar_spikes_hhe.py` | D4: spikes do HHE congelado |
| `scripts/features_ruido.py` | D5: features de ruído |
| `scripts/treinar_DET.py` | D6: treino do detector (`--componentes NZ` = sem o HHE) |
| `scripts/escolher_dias_validacao.py` | D7a: dias de validação |
| `scripts/prob_em_eventos.py` | D7a: prob. do detector em volta de eventos do catálogo |
| `scripts/e3ws_dia.py` | D7b: E3WS em dias inteiros (detector 3C ou NZ) |
| `scripts/avaliar_validacao.py` | D7c: avaliação e figuras |
| `scripts/analisar_probabilidades.py` | D7d: probabilidades e gatilho por dia |
| `scripts/prob_em_disparos_stalta.py` | D7d: prob. do detector nos maiores disparos do STA/LTA |
| `scripts/testar_picker.py` | D7d: o picker funciona na ISPT? |
| `scripts/plot_glitch_hhe.py` | D7d: alarme falso das 15:03 do dia 164 |
| `RELATORIO_validacao.md` | relatório da validação para o Pablo (3C × NZ) |
| `scripts/figuras_relatorio.py` | figuras para o Pablo: matrizes de confusão e tabela comparativa (`results/fig_*.png`) |
| `scripts/gerar_relatorio_docx.py` | relatório Word do treino e da validação (`RELATORIO_treino_validacao_ISPT2014.docx`; precisa de `pip install python-docx`; rode antes o `figuras_relatorio.py`) |
| `functions/` | funções do E3WS na versão do Pablo (StationXML) |
| `pz/` | `pb_ISPT.xml` (StationXML) e PZ de 2014 |
| `results/` | saídas pequenas (CSV, TXT, PNG) |
| `treino_DET/` | dados de treino (**fora do git**, grandes; refaça com D2 e D5) |
