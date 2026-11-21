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
- Features de ruído prontas (GUIA D5, ~1,5 h com 14 processos): 2.592.000 janelas nos 30 dias,
  **82 % mascaradas** pelo STA/LTA, 6.615 descartadas por falha, **461.954 janelas de ruído úteis**
  (2,2 GB). Por dia: de 2.292 (dia 355) a 39.635. É metade da meta do Pablo (900 mil), mas ainda
  ~2,8× o número de janelas de terremotos (167 mil). Decisão: treinar com isso e, se a validação
  mostrar falsos alarmes demais, acrescentar dias ou afrouxar a máscara.
- Ponto de atenção: a máscara deixa só os trechos mais calmos de cada dia. O detector pode ver
  pouco do ruído "agitado" (mar forte, ruído impulsivo) e disparar nele. A validação (D7) vai mostrar.

## 2026-11-21

### 8. Orientação do Pablo e versão 2 do treino
O Pablo orientou:
- usar **900 mil janelas de ruído** (baseline; pode ser mais);
- treinar com **o ano todo**: no período do HHE congelado aparecem spikes, e o detector precisa
  aprender que isso também é ruído.

O que os dados mostram (`scripts/investigar_spikes_hhe.py`, dia 60):
- o HHE fica parado em **−8.382.254 contagens** em 10.799.681 de 10.799.994 amostras. É quase o
  limite negativo do conversor de 24 bits (−8.388.608): o canal está **saturado**, não "desligado";
- 4 spikes no dia, de 0,4 a 0,8 s, com milhões de contagens. Alguns coincidem com falhas curtas de
  dados (o trecho fica em 0 nos 3 canais);
- o HHZ e o HHN também mostram pulsos curtos.

Teste das features com o HHE congelado: 10 das 140 features viram NaN (não há como calcular, por
exemplo, a entropia de um sinal constante); nenhuma vira infinito. O XGBoost aceita NaN.

Comparação das máscaras de eventos num dia (passo D5):

| Máscara | Como funciona | Apaga |
|---|---|---|
| v1 (minha) | STA/LTA curto (0,5 s/10 s), limiar 4, apaga [−15 s, +45 s] de cada disparo | **82 %** das janelas |
| v2 (Pablo, `gen_catag.py`) | STA/LTA longo (60 s/240 s), limiar 2,8, só eventos < 10 min, ±60 s | **~1 %** do dia (dia 191); ~9 % numa hora do dia 59 |

A máscara v1 apagava também os spikes e o ruído impulsivo, justamente o que o detector deve
aprender a ignorar. A v2 é o baseline do Pablo. Contrapartida: microssismos pequenos entram no
treino como "ruído", então o detector tende a ser menos sensível aos menores eventos e a dar menos
alarmes falsos.

Mudanças (versão 2):
- `escolher_dias_ruido.py`: ano inteiro, 2 dias sorteados por mês → 24 dias (13 com HHE congelado);
- `features_ruido.py`: máscara do Pablo, passo de 2 s, **mantém** janelas com HHE congelado;
- `treinar_DET.py`: sorteia 900 mil janelas de ruído e mostra os falsos alarmes separados
  (HHE congelado × normal);
- os três scripts reescritos com todas as linhas comentadas;
- versão 1 guardada em `treino_DET/atr_noise/ISPT_v1_mascara_estrita/` e `results/dias_ruido_v1.csv`.

**Resultado das features de ruído v2** (`results/features_ruido_log.txt`, ~35 min com 14 processos):
- 1.036.800 janelas nos 24 dias; **5.547 mascaradas (0,5 %)**; 1.812 com falha; **1.029.441 úteis**
  (4,3 GB), acima da meta de 900 mil;
- de 0 a 4 eventos fortes apagados por dia; cada dia ficou com ~42–43 mil janelas;
- todas as janelas dos dias com HHE congelado têm NaN (ex.: dia 59, 42.867 de 42.867); nenhuma nos
  dias normais (ex.: dia 300). Proporção no treino: 13 dias congelados × 11 normais.

### 9. Treino do detector v2 (`results/treino_DET_log.txt`, 22,8 min na RTX 3050)
- Terremotos: 167.525 janelas de 21.778 terremotos (70.193 P, 97.332 S).
- Ruído: 1.029.441 janelas (557.944 com NaN = HHE congelado); 900 mil sorteadas.
- Teste 90/10 (10,4 min): 106.155 janelas.

| verdade \ previsto | ruído | P | S |
|---|---|---|---|
| ruído (90.000) | 90.000 | 0 | 0 |
| P (6.705) | 0 | 6.639 | 66 |
| S (9.450) | 2 | 35 | 9.413 |

  Com limiar 0,80 / 0,90 / 0,95: acerta 98,4 / 98,0 / 97,6 % das janelas P; **nenhuma** janela de
  ruído vira P (nem com HHE congelado, nem normal).
- Modelo final (12,0 min): `treino_DET/saved_models/DET_ISPT_Whole_XGB_10tp3.0to3.0each0.5f7_unbalanced_official_v16.joblib` (4,3 MB).

**Cuidado ao interpretar, o resultado está otimista demais:**
1. o ruído de teste vem dos **mesmos 24 dias** do treino. Com passo de 2 s, janelas vizinhas
   compartilham 8 s de sinal, então o modelo "já viu" quase o mesmo ruído;
2. os terremotos do `atr_eq` são de outras estações, com outro ruído de fundo. Separar "ruído da
   ISPT" de "terremoto de outra estação" é mais fácil do que separar ruído da ISPT de um
   **microssismo registrado na ISPT**, que é o caso real.
O teste que importa é o **D7**: rodar o E3WS em dados contínuos de dias de validação, contar os
alarmes falsos por dia e ver quantos eventos do IG-EPN são encontrados.

**Consequência para a análise:** com o detector treinado no ano todo, dá para **detectar** no
1º semestre. Mas a magnitude, a distância e principalmente o back-azimuth usam o HHE, então as
estimativas de fonte do 1º semestre devem ser tratadas com cautela (ou usar só a contagem de eventos).
- `pandas==1.5.3` e `gdown` adicionados ao ambiente.
