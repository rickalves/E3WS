# Experimento 01: teste inicial

**Data:** 2026-11-15
**Objetivo:** confirmar que a instalação reproduz o resultado de referência do autor.

## Configuração

Script `real_time/E3WS_rt.py` sem alterações:

| Variável | Valor | Significado |
|---|---|---|
| `n_models` | 5 | Estimativas de magnitude, distância e profundidade com 3 a 7 s de onda P |
| `n_models_baz` | 1 | Back-azimuth só com 3 s de onda P |
| `thr` | 0.80 | Limiar do detector (média das 3 últimas probabilidades de P) |
| `pb_inst` | True | Correção da resposta do sensor com `pz/SLRZ_HN.pz` |

Evento: Canta, M5,6, 07/01/2022, estação SLRZ.

## Resultado

Chegada da onda P marcada pelo picker: 2022-01-07T10:27:23,6 UTC.

| P (s) | Magnitude | Distância (km) | Profundidade (km) | Back-azimuth (°) |
|---|---|---|---|---|
| 3 | 5,34 | 70,7 | 38,2 | −124,3 |
| 4 | 5,33 | 63,4 | 27,9 | −124,3 |
| 5 | 5,56 | 61,7 | 26,9 | −124,3 |
| 6 | 5,40 | 64,7 | 32,4 | −124,3 |
| 7 | 5,49 | 66,0 | 34,6 | −124,3 |

Arquivos: [resultado_SLRZ_Canta_M5.6.csv](resultado_SLRZ_Canta_M5.6.csv) e
[grafico_deteccao.png](grafico_deteccao.png).

## Comparação com a referência do autor

- Chegada da P, magnitude, distância e profundidade: **idênticas** a
  `real_time/results/SLRZ_Canta_M5.6_20220107.csv`, até a última casa decimal.
- Back-azimuth (e latitude/longitude): iguais aos 3 s. Depois disso a referência muda para
  −137° / −136°, porque o autor rodou com mais modelos de back-azimuth (`n_models_baz > 1`).
  Com `n_models_baz = 1`, o valor de 3 s é repetido nas linhas seguintes.

## Conclusão

O ambiente reproduz o algoritmo fielmente. A magnitude começa em 5,3 com 3 s de P e se aproxima
do valor do catálogo (5,6) com mais segundos de sinal.
