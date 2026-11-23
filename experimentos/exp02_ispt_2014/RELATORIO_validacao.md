# Relatório: validação do detector da ISPT (2014), com HHE × sem HHE

**Data:** 2026-11-23 · **Branch:** `experimentos` · **Detalhes e comandos:** GUIA D6–D7, DIARIO itens 9–13

## 1. Contexto

- O canal **HHE da ISPT está congelado de 01/01 a 08/07/2014**. Ele fica saturado em −8.382.254
  contagens, com spikes ocasionais. Nas janelas congeladas, as 45 features do E saem NaN.
- Seguindo a orientação do Pablo, o detector foi treinado com ruído do **ano inteiro**:
  - 24 dias, 2 por mês, 13 deles com o HHE congelado;
  - ~1,03 milhão de janelas de ruído;
  - máscara de eventos do `gen_catag`.
  - Os exemplos de terremoto vêm do `atr_eq` oficial (M ≥ 3).
- Foram testadas as duas formas pedidas:

| Detector | Features | Arquivo |
|---|---|---|
| **3C** (com HHE) | 140 (E, N, Z + 5 cruzadas) | `DET_ISPT_Whole_XGB_..._v16.joblib` |
| **NZ** (sem HHE) | 90 (só N e Z) | `DET_ISPT_NZ_Whole_XGB_..._v16.joblib` |

## 2. Como foi validado

- 13 dias inteiros que **não** entraram no treino (86.400 janelas de 10 s por dia, passo de 1 s).
  Gatilho igual ao `E3WS_rt.py`: média de 3 prob. de P ≥ limiar; rearme quando a média de 5 prob. de
  ruído ≥ 0,99.
  - 6 dias calmos: 3 com HHE congelado, 3 normais.
  - 7 dias com eventos IG-EPN a < 200 km.
- **Referência:** a cópia do catálogo IG-EPN da pasta do Pablo (`cat_origen_2012_sep2023.txt`), que
  só tem M ≥ ~3,5. São **9 eventos** a < 200 km nesses dias.
- **"Encontrou" significa:** a P do E3WS cai entre a origem − 5 s e a origem + dist/5,5 + 15 s.

## 3. Resultados

### 3.1 Eventos do catálogo encontrados (limiar 0,80)

| Evento IG-EPN | M | Dist. (km) | HHE | 3C | NZ |
|---|---|---|---|---|---|
| 02/01 08:42 | 3,9 | 148 | congelado | – | **sim** (0,95) |
| 05/01 16:29 | 3,7 | 184 (63 km prof.) | congelado | – | – |
| 13/06 18:10 | 4,6 | 14 | congelado | – | **sim** (1,00) |
| 13/06 19:16 | 3,8 | 11 | congelado | – | **sim** (0,98) |
| 02/07 16:10 | 3,6 | 151 | congelado | – | – |
| 18/07 12:08 | 4,1 | 108 | normal | – | – |
| 01/08 10:05 | 3,9 | 112 | normal | **sim** (0,84) | **sim** (0,87) |
| 05/09 05:38 | 3,6 | 104 (49 km prof.) | normal | – | – |
| 05/09 20:50 | 3,9 | 64 | normal | **sim** (0,99) | **sim** (0,87) |
| **Total** | | | | **2/9** | **5/9** |

Nos limiares 0,90 e 0,95, o 3C acha 1/9 e 1/9, e o NZ acha 3/9 e 2/9.

### 3.2 Detecções por dia e alarmes falsos

- **3C:** 5 detecções. **NZ:** 10 detecções. As 5 do 3C também estão no NZ (P a menos de 5 s).
- **Dias calmos:** 1 detecção em 6 dias, nos dois detectores (14/07 23:46:56). Na figura, P e S
  estão nítidas, com S−P ≈ 2,3 s (~19 km); o E3WS estimou M3,0. É um microssismo real, fora do
  catálogo porque o catálogo só tem M ≥ 3,5.
- As detecções do NZ que não estão no catálogo, no dia 164 às 18:40 e 18:45 (M ~3,7, 15–24 km), têm
  cara de réplicas do M4,6. Ainda não foram conferidas no sismograma.
- **Único alarme falso identificado:** 13/06 às 15:03:26, nos **dois** detectores. É o instante em que
  o HHE volta a congelar: ele salta para −8,38 milhões de contagens e, no mesmo instante, aparece um
  pulso curto em N e Z. É um glitch do instrumento, não um terremoto (figura
  `results/evento_dia164_1503.png`). Antes desse instante, o HHE estava "vivo" (perto de 0), ou seja,
  **o período congelado tem intervalos curtos em que o canal volta**.

### 3.3 Fonte (46 s de P), nos 5 eventos achados

| Evento | M cat. | M E3WS | Dist. cat. | Dist. E3WS |
|---|---|---|---|---|
| 02/01 08:42 | 3,9 | 4,09 | 148 | 111 |
| 13/06 18:10 | 4,6 | 4,51 | 14 | 19 |
| 13/06 19:16 | 3,8 | 4,05 | 11 | 25 |
| 01/08 10:05 | 3,9 | 4,04 | 112 | 114 |
| 05/09 20:50 | 3,9 | 3,87 | 64 | 77 |

Magnitude a ±0,25 e distância razoável. O back-azimuth no 1º semestre não tem sentido físico,
porque depende do E.

## 4. Problemas encontrados

### 4.1 Com o HHE (3C), o detector aprende um atalho
No treino, todas as janelas com o E congelado (NaN) eram ruído. Por isso o 3C aprendeu a regra
"E congelado ⇒ ruído" e **não detecta nenhum evento no 1º semestre** (0/5 eventos; probabilidade de
P ≤ 0,001 até no M4,6 a 14 km). **Sem o HHE (NZ), o problema some**: 3/5 no 1º semestre e o mesmo
desempenho do 3C no 2º. **Recomendação: usar o NZ para 2014.**

### 4.2 O picker genérico não funciona na ISPT
Script: `scripts/testar_picker.py`; saída: `results/testar_picker.txt`.

| Caso | HHE real | E = cópia do N | E congelado |
|---|---|---|---|
| 05/09 20:50 M3,9 | 0,003 | 0,003 | 0,977 |
| 01/08 10:05 M3,9 | 0,002 | 0,001 | 0,993 |
| 13/06 18:10 M4,6 (E já congelado) | 0,990 | 0,001 | 0,990 |

- Com os dados reais, o picker (`PICK_CLF_..._v16.joblib`, `pb_inst=True` e StationXML, a mesma
  configuração do `E3WS_Ecuador.py`) dá prob. máxima de P ≈ 0,001–0,003, mesmo em terremotos claros.
- Ele só dá ~0,99 quando o E está congelado (features NaN), e isso é artefato, não pick.
- A hora da P passa a ser o argmax de uma curva quase plana. Mesmo assim, a magnitude e a distância
  ficaram razoáveis, porque o erro do pick fica em poucos segundos dentro da janela de 8 s.
- **Pergunta ao Pablo:** o picker funcionou na SALI? Faz sentido treinar um picker para a ISPT, ou
  usar um pick clássico (AIC ou STA/LTA) dentro da janela que disparou?

### 4.3 Baixa sensibilidade para microssismos
Scripts: `analisar_probabilidades.py` e `prob_em_disparos_stalta.py`; DIARIO item 12.

- O gatilho não fica travado: a condição de rearme vale em 99–100 % das janelas.
- O detector simplesmente diz "ruído" para os eventos pequenos. No dia 195 (1.592 disparos do
  STA/LTA), só o evento de 13,8 µm/s teve P ≈ 1 (0,999 no NZ, 0,998 no 3C). Disparos de 0,2–2,3 µm/s
  tiveram P ≤ 0,17.
- Causas prováveis:
  - o `atr_eq` só tem M ≥ 3;
  - a máscara do `gen_catag` (STA/LTA 60/240 s) deixa os microssismos dentro do ruído, então o
    detector aprende que eles são ruído.
- **Consequência:** o detector serve para eventos de ~M3 para cima. Ele **não serve para contar a
  microssismicidade** da ilha, que é o que interessa para a correlação com SSE.
- **Opções para discutir:**
  1. aceitar a completude ~M3;
  2. retreinar com a máscara estrita (v1: STA/LTA 0,5/10 s, que tira os microssismos do ruído);
  3. incluir exemplos de eventos pequenos no `atr_eq`;
  4. complementar com outro método para os eventos menores.

## 5. Resumo

| | 3C (com HHE) | NZ (sem HHE) |
|---|---|---|
| Eventos IG-EPN achados (lim. 0,80) | 2/9 | **5/9** |
| 1º semestre (HHE congelado) | 0/5 | **3/5** |
| 2º semestre | 2/4 | 2/4 |
| Alarmes falsos em 13 dias | 1 (glitch do HHE) | 1 (o mesmo) |
| Microssismos | não detecta | não detecta |

Pedidos pendentes ao Pablo:
- o catálogo IG-EPN 2014 com todas as magnitudes, para medir a completude abaixo de M3,5;
- a série de taxa de momento do GNSS.
