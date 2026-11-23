# Conceitos usados no experimento

Explicações curtas, na ordem em que aparecem no trabalho. Volte aqui sempre que um termo do
[GUIA.md](GUIA.md) não estiver claro.

## Sismômetro, estação e canais

- **Estação**: o lugar onde fica o sensor. A **ISPT** fica na Isla de la Plata (Equador), a **SALI**
  em Salinas, a **SLRZ** em Lima. **EC** é o código da rede do IG-EPN.
- **Componentes**: o sensor mede o movimento do chão em 3 direções: **E** (leste), **N** (norte),
  **Z** (vertical).
- **Nome do canal**, ex. **HHZ**: 1ª letra = taxa de amostragem alta (H, ≥ 80 Hz); 2ª letra = sensor
  de velocidade (H, sismômetro de banda larga; N seria acelerômetro, como o HN da SLRZ);
  3ª = componente.
- **Taxa de amostragem**: quantas medidas por segundo. A ISPT grava 125 Hz em 2014; o E3WS
  reamostra tudo para 100 Hz.
- **Canal morto/congelado**: o canal grava sempre o mesmo número. Foi o que aconteceu com o HHE da
  ISPT de 01/01 a 08/07/2014: ficou parado em −8.382.254, quase o limite do conversor de 24 bits
  (−8.388.608). Isso é **saturação**: o sensor "encostou" no limite e não registra mais movimento.
- **Spike (pico)**: valor absurdo que aparece e some em menos de 1 s. Não é movimento do chão, é
  defeito eletrônico ou de transmissão. O detector precisa aprender que spike é ruído.
- **NaN** ("not a number"): valor que não pode ser calculado, por exemplo a entropia de um sinal
  constante. O XGBoost trata NaN como "informação ausente".

## Resposta do instrumento

- O sensor não grava metros nem m/s, grava **contagens** (números do conversor). A **resposta do
  instrumento** é a "fórmula" que converte contagens em movimento real do chão.
- **PZ (polos e zeros)** e **StationXML** são dois formatos que guardam essa fórmula.
  O StationXML guarda todas as **épocas** (períodos em que a configuração do sensor foi a mesma).
  A ISPT mudou de época em 08/07/2014 18:30.
- O E3WS converte tudo para **aceleração (m/s²)**. Assim, um terremoto "parece" igual em qualquer
  sensor, e modelos treinados com dados do mundo todo funcionam em qualquer estação.

## Ondas e eventos

- **Onda P** (primária): a primeira a chegar, mais rápida e mais fraca.
- **Onda S** (secundária): chega depois, normalmente maior. Depois vem a **coda**, a "cauda" do sinal.
- **S − P**: o tempo entre a P e a S cresce com a distância. Regra prática: distância (km) ≈ 8 × (S − P em segundos).
  Ex.: S − P = 3 s → ~25 km.
- **Microssismo**: terremoto muito pequeno, sentido só pelos instrumentos. A ISPT registra muitos.
- **Telessismo**: terremoto grande e distante (outro continente). Suas **ondas de superfície**
  chacoalham a estação por horas e podem **disparar** pequenos sismos locais (Tabela 4.1 da tese).
- **Enxame (swarm)**: muitos sismos parecidos num curto período, sem um "principal" claro.
- **Réplicas (aftershocks)**: sismos que seguem um terremoto principal.

## Catálogos

- **Catálogo sísmico**: tabela com um terremoto por linha (hora, posição, profundidade, magnitude).
- **USGS** (Serviço Geológico dos EUA): catálogo **global**; no Equador só registra eventos de ~M4 para cima.
- **IG-EPN** (Instituto Geofísico da Escuela Politécnica Nacional, Quito): rede **nacional** do
  Equador, com estações perto dos eventos; registra eventos bem menores (~M2). Opera a ISPT.
- **Magnitude de completude (Mc)**: abaixo dela o catálogo perde eventos. Comparar contagens só faz
  sentido acima do Mc.
- **Gutenberg–Richter**: em qualquer região há ~10 vezes mais sismos a cada magnitude a menos. Usado para estimar o Mc.
- **Declustering**: separar réplicas e enxames da sismicidade "de fundo", para testar tendências.

## Momento, slow slip e GNSS

- **Momento sísmico (M₀)** = rigidez da rocha × área da falha que escorregou × quanto escorregou.
  Unidade N·m. A magnitude **Mw** é uma escala logarítmica do M₀ (+1 em Mw ≈ 32× mais momento).
- **Slow slip event (SSE)**: a falha escorrega **devagar** (dias a meses). Não gera ondas, então o
  sismômetro não vê, mas o chão se desloca alguns milímetros.
- **GNSS** (GPS e similares): antenas fixas medem a posição do chão com precisão de milímetros. Com
  várias antenas, estima-se quanto a falha escorregou e quanto momento foi liberado.
- **Taxa de momento**: momento liberado por unidade de tempo. Picos = falha escorregando mais rápido.
  Na tese, os picos de taxa de momento **antecedem** enxames (clusters 8 e 14).

## STA/LTA

Detector clássico e simples: compara a energia média **curta** (STA, ex. 0,5 s) com a **longa**
(LTA, ex. 10 s). Se a razão passa de um limiar (ex. 4), "disparou": chegou algo mais forte que o
ruído de fundo. Não diferencia terremoto de ruído impulsivo, por isso é usado aqui só para achar
e **mascarar** possíveis eventos nos dias de ruído.

## O E3WS

Três etapas, todas com aprendizado de máquina (XGBoost):
1. **Detector (DET)**: olha janelas de 10 s, andando de 1 em 1 s, e dá a probabilidade de ser
   **ruído, P ou S**. Dispara quando a média de 3 janelas seguidas de P passa do **limiar** (`thr`).
   **Depende da estação**, porque precisa conhecer o ruído do local.
2. **Picker (PICK)**: marca o instante exato da chegada da P.
3. **Fonte**: modelos de **magnitude (MAG)**, **distância (DIS)**, **profundidade (DEP)** e
   **back-azimuth (BAZ)**, a direção de onde vem a onda. `7tp3f45` = usa 7 s antes e 3 s depois da P,
   com filtro até 45 Hz. Com uma estação só, o BAZ é o parâmetro menos confiável.

- **Features (atributos)**: os 140 números que resumem uma janela (energia, frequências,
  polarização, MFCC etc.). O modelo não vê o sinal, vê esses números.
- **`atr_eq`**: tabela com as features de ~167 mil janelas de **terremotos reais** do mundo todo,
  rotuladas como P ou S. `DET_7.00tp3.00` = janela com 7 s antes e 3 s depois da fase.
- **Ruído da estação**: features de janelas **sem** terremoto da própria estação. Junto com o `atr_eq`,
  forma o conjunto de treino do detector.

## Aprendizado de máquina

- **XGBoost**: modelo feito de muitas **árvores de decisão** pequenas, cada uma corrigindo os erros
  das anteriores. O detector usa 6000 árvores de profundidade 4.
- **Treino / teste**: o modelo aprende com uma parte dos dados e é avaliado em outra, que ele nunca
  viu. No teste separamos **terremotos inteiros**, não janelas soltas, para não "colar".
- **Matriz de confusão**: tabela verdade × previsto. Ex.: quantas janelas de ruído o modelo chamou de P.
- **Falso alarme**: o detector dispara sem terremoto. É a métrica mais importante em dados contínuos:
  um dia tem 86.400 janelas, então mesmo 0,01 % de erro vira ~9 alarmes falsos por dia.
- **Limiar (`thr`)**: probabilidade mínima de P para disparar. Mais alto = menos falsos alarmes, mas
  mais eventos pequenos perdidos. O Pablo usou 0,95 no Equador; o exemplo do repositório usa 0,80.
- **Vazamento de dados (data leakage)**: quando o teste tem exemplos quase iguais aos do treino.
  - O modelo "reconhece" em vez de "entender", e a nota do teste sai inflada.
  - Exemplo: janelas de ruído vizinhas compartilham 8 dos 10 s. Se forem sorteadas uma a uma,
    quase toda janela do teste tem uma "irmã" no treino.
  - Correção: separar por **dia** (ou por evento), nunca por janela.
- **Mudança de domínio (domain shift)**: os dados reais são diferentes dos dados de treino.
  - Pode ser outra estação, outro instrumento, outro nível de ruído ou outra região.
  - O modelo vai bem no teste, que se parece com o treino, e mal na prática.
- **Atalho (shortcut learning)**: o modelo aprende uma pista fácil que separa as classes no treino,
  mas não tem relação com o que queremos.
  - Exemplo 1: "E congelado ⇒ ruído".
  - Exemplo 2: "parece o fundo da ISPT ⇒ ruído", porque todo o ruído do treino é da ISPT e nenhum
    terremoto é.
  - Um teste com os mesmos vieses do treino **não consegue** revelar um atalho; só dados novos e
    diferentes revelam.
