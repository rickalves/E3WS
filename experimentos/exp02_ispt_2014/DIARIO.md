# Diário do experimento 02

Descobertas na ordem em que apareceram, com os números e de onde vieram.
Para reproduzir, veja o passo indicado em [GUIA.md](GUIA.md).

## 2026-11-20

### 1. Os dados de 2014 (GUIA B1)
- 365 dias × 3 canais (HHE/HHN/HHZ), 125 Hz, location `00`, 17 GB, estrutura SDS.
- Só os dias 189, 361 e 363 têm < 23 h. 117 dias têm sobreposições entre traces (resolvidas com `merge`).
- Sensor Güralp CMG3-ESPC, com duas épocas em 2014: troca em **2014-07-08 18:30** (StationXML).
  O ganho difere < 1 % entre elas.
- O `pb_ISPT.pz` do Drive tem 96 blocos (vários canais e épocas). O `attach_paz` da ObsPy fica com o
  último bloco lido, então ele não serve direto para o E3WS do repositório (GUIA C1).

### 2. O detector da SLRZ não serve na ISPT (GUIA C2, B3)
Teste de 1,5 h em volta do evento USGS de 2014-06-13 18:10:50 (mb 4,4, 11 km da ISPT):
- 94 % das janelas de ruído com prob. de P > 0,8; prob. de ruído ≈ 0. O gatilho nunca rearma.
- A correção de instrumento está certa: o ruído da ISPT (~5×10⁻⁷ m/s², 1–7 Hz) é **14× menor** que
  o da SLRZ (~6,5×10⁻⁶ m/s², acelerômetro urbano). O detector nunca viu um ruído tão baixo.
- Conclusão: treinar um detector próprio da ISPT, como manda o README do autor.

### 3. Picker e modelos de fonte funcionam (GUIA C3)

| | USGS | E3WS 3 s | E3WS 46 s |
|---|---|---|---|
| Magnitude | 4,4 (mb) | 4,57 | 5,22 |
| Distância (km) | 11 | 25,4 | 8,0 |
| Profundidade (km) | 44 | 64,6 | 17,5 |
| Back-azimuth (°) | ≈ 55 | 5,4 | −24,9 |

A distância com 46 s é boa; a magnitude fica acima do mb do USGS (comparar com o IG-EPN antes de
concluir). O STA/LTA também dispara às 18:06:48, 18:08:01, 18:09:59, 18:12:23 e 18:12:56: possíveis
pré e pós-abalos, ainda não conferidos no sismograma.

**Custo:** features ~29 ms/janela; DET 5 ms por chamada, mas 0,04 ms/janela em lote. Um ano tem
~31,5 milhões de janelas. A versão de teste levaria ~250 h; com blocos diários e DET em lote, ~15–25 h.

### 4. Material do Pablo em `D:\Downloads\E3WS_Ecuador\E3WS_Ecuador`

| Item | Caminho | Observação |
|---|---|---|
| DET da SALI treinado | `old/saved_models_GPU/DET_SALI_..._v16.joblib` | Não há DET da ISPT (o Pablo confirmou) |
| Catálogo IG-EPN 2012–set/2023 | `old/Catalogo/pb_csv/cat_origen_*`, `cat_magnitud_*`, `cat_picks_*` | Só M ≥ 3,5 (216 eventos no Equador em 2014; 53 a < 200 km da ISPT) |
| Resultados E3WS do Pablo | `new/Figs/E3WS_ISPT.csv` (2009–2021), `E3WS_SALI.csv` (2013–2020) | |
| Ruído da ISPT em features | `old/atr/ISPT/*.csv` (11 dias, um por ano, nenhum de 2014) | |
| Script de treino | `old/pb_save_trainingmodel_official_LOO_Ecuador.py` | Só `atr_eq` tp3.00, XGBoost na GPU, `thr = 0.95` |
| Funções do E3WS | `functions/` | `st_FV` usa `remove_response` com StationXML (o repositório usa PZ) |

### 5. Canal HHE morto de 01/01 a 08/07/2014 (GUIA B2, B3, B5)
- 183 dias com o HHE congelado (1 valor distinto). HHN e HHZ estão bons o ano todo.
- Em aceleração, o HHE dá exatamente 0 até o dia 188 e valores normais a partir do dia 190.
- Na rodada do Pablo: ~1000 detecções/mês até julho e ~30/mês depois. Só 28 de 7135 do 1º semestre
  estão a < 60 s de um evento IG-EPN. O IG-EPN tem ~4 eventos/mês (M ≥ 3,5, < 200 km) o ano todo.
  Logo, as detecções do 1º semestre são, quase todas, falsas.
- **Inferência (não confirmada):** a troca de época de 08/07 foi uma intervenção que consertou o canal.
- Decisão: analisar só **2014-07-09 a 2014-12-31**.
- Lição: se a contagem de sismos muda bruscamente numa data de manutenção, desconfie do instrumento.

### 6. A "calma" da ilha tem muitos microssismos (GUIA D3, D4)
- O STA/LTA (0,5 s / 10 s, 2–15 Hz, limiar 4) dispara 1000 a 4000 vezes por dia (mediana 2748).
- No dia mais calmo (191), os maiores disparos são **microssismos reais**, com P e S claras
  (S − P de 3 s a 11 s, ou seja, ~25 a 90 km). Figura: `results/disparos_stalta_dia191.png`.
- Consequência: nos dias de ruído, apagar [−15 s, +45 s] em volta de cada disparo. Isso remove
  metade ou mais das janelas, então foram usados **30 dias** de treino em vez de ~10.
- Boa notícia para a pesquisa: a ISPT deve detectar muitos eventos pequenos.

### 7. Preparação do treino (GUIA D1–D6)
- `atr_eq` tp3.00 baixado (549 MB, 167.525 janelas).
- 30 dias de treino escolhidos (`results/dias_ruido.csv`), entre 10/07 e 27/12.
- GPU RTX 3050 funciona com o XGBoost 1.6.1 (`gpu_hist`).
- Cálculo das features de ruído iniciado (GUIA D5).
- `pandas==1.5.3` e `gdown` adicionados ao ambiente.
