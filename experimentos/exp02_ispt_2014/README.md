# Experimento 02: sismicidade de 2014 na estação ISPT (Isla de la Plata) com o E3WS

**Início:** 2026-11-20
**Objetivo:** reproduzir, para a estação ISPT e o ano de 2014, o procedimento da tese de Pablo Lara
(seção 4.3, "Characterizing the seismicity during a multi-year long period in Ecuador"). A ideia é
montar um catálogo de uma estação só, ver se a sismicidade aumentou ao longo do ano e se os enxames
se correlacionam com slow slip events (SSE) e com a taxa de momento do GNSS.

A tese usou a estação SALI (Salinas, ~160 km dos enxames). A ISPT fica na própria Ilha de La Plata,
em cima da zona de SSE, então deve detectar eventos menores e mais próximos.

## Como ler esta pasta

| Arquivo | Para quê |
|---|---|
| [GUIA.md](GUIA.md) | **Passo a passo reproduzível**: comandos, entradas, saídas, resultado esperado |
| [CONCEITOS.md](CONCEITOS.md) | Explicação dos termos de sismologia e de aprendizado de máquina |
| [DIARIO.md](DIARIO.md) | Descobertas em ordem, com os números |
| `scripts/` | Todos os scripts (mapa no fim do GUIA) |
| `results/` | Saídas pequenas (CSV, TXT, PNG) |
| `treino_DET/` | Dados de treino grandes, **fora do git** (refaça com o GUIA D2 e D5) |

## Estado atual

- [x] Ambiente e modelos (GUIA A)
- [x] Conhecer os dados: canal HHE congelado (saturado) até 08/07/2014 (GUIA B)
- [x] Teste com o detector da SLRZ: não serve na ISPT → treinar detector próprio (GUIA C)
- [x] `atr_eq` baixado (GUIA D2)
- [x] Versão 1 do ruído (só 2º semestre, máscara estrita): 462 mil janelas. Substituída pela v2 por orientação do Pablo
- [x] Versão 2: 24 dias do ano inteiro escolhidos, 13 com HHE congelado (GUIA D3)
- [x] Features de ruído v2: 1.029.441 janelas úteis em 24 dias, 0,5 % mascaradas (GUIA D5)
- [x] Treinar o detector da ISPT (GUIA D6): 22,8 min; no teste 90/10, 0 de 90 mil janelas de ruído viraram P (otimista, ver DIARIO item 9)
- [x] Detector sem HHE (NZ), porque o 3C não enxerga terremotos com o HHE congelado (DIARIO item 10)
- [ ] Validar os dois detectores (GUIA D7): **NZ concluído**; 3C parado (DIARIO item 11; investigar a lentidão antes)
- [ ] Rodar 09/07–31/12/2014 inteiro e montar o catálogo
- [ ] Análise da sismicidade e correlação com GNSS

**Pedido ao Pablo:** catálogo IG-EPN 2014 da região de La Plata com todas as magnitudes (a cópia
atual só tem M ≥ 3,5) e a série de taxa de momento GNSS (Nocquet, 2023).

## Plano

### Fase 1: detector da ISPT
Treinar (GUIA D) e validar: falsos alarmes por dia em dias de validação e quantos eventos do IG-EPN
são encontrados. Ajustar o limiar (`thr`) se preciso.

### Fase 2: rodar o período
1. Adaptar `e3ws_continuo.py`: funções do Pablo (StationXML), detector da ISPT, um bloco por dia,
   DET em lote, checkpoint diário.
2. Rodar 09/07–31/12/2014 com caracterização a 3 s e 46 s.

### Fase 3: limpar e validar o catálogo
1. Remover detecções espúrias (pick fraco, prob. baixa, janelas com falha, ondas de superfície).
2. Comparar com o IG-EPN e o USGS: eventos encontrados por magnitude e distância, viés de magnitude.
3. Separar por distância estimada (ex.: < 50 km = La Plata) e calcular o Mc por mês.

### Fase 4: a sismicidade aumentou?
1. Taxa diária/semanal com M ≥ Mc, curva acumulada, momento sísmico acumulado.
2. Declustering e teste de tendência da sismicidade de fundo.
3. Tabela de clusters como a Tabela 4.1 da tese: réplicas, disparados por telessismos, candidatos a SSE.
4. Comparar com o catálogo da SALI do Pablo (`E3WS_SALI.csv`), que cobre 2014 inteiro.

### Fase 5: correlação com slow slip e taxa de momento
Correlação cruzada (com defasagem) entre a taxa de sismicidade e a taxa de momento do GNSS.
