# -*- coding: utf-8 -*-
"""PASSO D6 - Treinar o detector (DET) do E3WS para a estacao ISPT.

Segue o script do Pablo (pb_save_trainingmodel_official_LOO_Ecuador.py):
  - TERREMOTOS: atr_eq DET_7.00tp3.00 = janelas de 10 s de terremotos reais do mundo todo,
    terminando 3 s depois da chegada da onda P (rotulo 1) ou da onda S (rotulo 2);
  - RUIDO: features da ISPT do passo D5 (rotulo 0); o baseline do Pablo sao 900 mil janelas;
  - MODELO: padronizacao (StandardScaler) + XGBoost com 6000 arvores de profundidade 4, na GPU.
Acrescimo didatico: antes do modelo final, treina com 90 % dos dados e testa nos 10 % restantes
(terremotos inteiros nunca vistos e ruido nunca visto), para medir os acertos e os falsos alarmes.

Uso (a partir de experimentos/exp02_ispt_2014):
  python scripts/treinar_DET.py treino_DET [--cpu] [--sem-teste] [--ruido N] [--componentes NZ]
    --cpu            treina no processador (sem GPU; bem mais lento)
    --sem-teste      pula o teste 90/10 (metade do tempo)
    --ruido N        quantas janelas de ruido usar (padrao 900000; 0 = todas)
    --componentes NZ usa so as 90 features dos componentes N e Z (sem nada do HHE).
                     Motivo: com o HHE congelado (jan-jul/2014), o detector de 3 componentes aprendeu
                     o atalho "HHE congelado = ruido" e nao detecta terremotos nesse periodo (DIARIO item 10).
"""
import sys                                       # argumentos da linha de comando
import os                                        # caminhos de arquivos
import glob                                      # listar arquivos com curinga (*)
import time                                      # medir o tempo
import numpy as np                               # contas com vetores
import pandas as pd                              # tabelas
import joblib                                    # salvar o modelo treinado
from sklearn.pipeline import make_pipeline       # encadear padronizacao + modelo
from sklearn.preprocessing import StandardScaler # padronizacao: cada feature com media 0 e desvio 1
from sklearn.metrics import confusion_matrix, classification_report   # metricas de acerto
import xgboost as xgb                            # o modelo (arvores de decisao com boosting)

np.random.seed(30002)                            # semente fixa: o resultado e reproduzivel

# --- Opcoes da linha de comando ---
PASTA = sys.argv[1]                              # pasta treino_DET
TREE = "hist" if "--cpu" in sys.argv else "gpu_hist"   # metodo do XGBoost: GPU (padrao) ou CPU
N_RUIDO = int(sys.argv[sys.argv.index("--ruido") + 1]) if "--ruido" in sys.argv else 900000   # baseline do Pablo
SO_NZ = "--componentes" in sys.argv and sys.argv[sys.argv.index("--componentes") + 1].upper() == "NZ"   # so N e Z?

# Colunas que o Pablo remove das features de terremotos (o ruido ja vem sem elas): 172 - 32 = 140
DEL_COL = ['lambda_2', 'lambda_3', 'E_maxturnpoints_t', 'N_maxturnpoints_t', 'Z_maxturnpoints_t',
           'E_IncDec_t', 'N_IncDec_t', 'Z_IncDec_t', 'E_growth_t', 'N_growth_t', 'Z_growth_t',
           'E_minturnpoints_t', 'N_minturnpoints_t', 'Z_minturnpoints_t',
           'E_maxturnpoints_f', 'N_maxturnpoints_f', 'Z_maxturnpoints_f',
           'E_minturnpoints_f', 'N_minturnpoints_f', 'Z_minturnpoints_f',
           'cov_EN', 'cov_EZ', 'cov_NZ', 'E_Erms_t', 'N_Erms_t', 'Z_Erms_t',
           'E_Etot_f', 'N_Etot_f', 'Z_Etot_f', 'E_Erms_f', 'N_Erms_f', 'Z_Erms_f']


def rotulo(psaft):
    """Converte o texto da coluna PSaft em numero: 'P+3.0' -> 1 (onda P), 'S+3.0' -> 2 (onda S).
    Regra do Pablo: so vale como P ou S se a fase chegou pelo menos 0,5 s antes do fim da janela."""
    fase = psaft[0]                              # primeira letra: 'P', 'S' ou 'N'
    tempo = float(psaft[1:].replace('+-', '-'))  # o numero: segundos depois da fase
    if fase == 'N' or tempo < 0.5:               # ruido, ou fase chegou tarde demais...
        return 0                                 # ...rotulo 0 (ruido)
    return 1 if fase == 'P' else 2               # P -> 1, S -> 2


def novo_modelo():
    """Cria o modelo com os mesmos parametros do Pablo."""
    return make_pipeline(
        StandardScaler(),                        # 1o: padroniza as features (aceita NaN: ignora no ajuste)
        xgb.XGBClassifier(                       # 2o: o classificador XGBoost
            tree_method=TREE,                    # GPU ou CPU
            n_estimators=6000,                   # numero de arvores
            max_depth=4,                         # profundidade maxima de cada arvore
            learning_rate=0.05,                  # quanto cada arvore corrige as anteriores
            colsample_bytree=0.4603,             # fracao das features sorteada para cada arvore
            subsample=0.8,                       # fracao das janelas sorteada para cada arvore
            gamma=0.0468, min_child_weight=1.7817,   # regras para nao dividir galhos sem ganho
            reg_alpha=0.4640, reg_lambda=0.8571, # regularizacao (evita decorar os dados)
            verbosity=0, nthread=-1))            # sem mensagens; usa todos os nucleos


inicio = time.time()                             # marca o inicio

# === 1. Exemplos de TERREMOTOS (atr_eq) ===
colunas_eq = pd.read_csv(os.path.join(PASTA, 'pb_index_DET_v16.csv')).feature.values   # nomes das 187 colunas
arquivos_eq = glob.glob(os.path.join(PASTA, 'atr_eq', 'DET_*tp*.csv'))   # o(s) arquivo(s) atr_eq
eq = pd.concat([pd.read_csv(f, header=None) for f in arquivos_eq], ignore_index=True)   # le (sem cabecalho)
eq.columns = colunas_eq                          # da nome as colunas
eq = eq.drop(columns=DEL_COL)                    # remove as 32 colunas que o Pablo nao usa
eq = eq[eq['ENZ_equal'] == 'ENZ_different'].reset_index(drop=True)   # so registros com E, N, Z diferentes
eq['y_label'] = eq['PSaft'].apply(rotulo)        # rotulo numerico (1 = P, 2 = S)
eq['evento'] = (eq['e_mag'].round(2).astype(str) + '_' + eq['eq_lat'].round(3).astype(str)
                + '_' + eq['eq_lon'].round(3).astype(str))   # identificador do terremoto (mag + posicao)
print('Terremotos: %d janelas de %d terremotos | rotulos: %s' % (
    len(eq), eq.evento.nunique(), eq.PSaft.value_counts().to_dict()))

# === 2. Exemplos de RUIDO da ISPT (passo D5) ===
colunas_ns = pd.read_csv(os.path.join(PASTA, 'pb_index_SASPe_official_v16.csv')).feature.values   # 143 nomes
arquivos_ns = sorted(glob.glob(os.path.join(PASTA, 'atr_noise', 'ISPT', 'DET_*.csv')))   # um arquivo por dia
ns = pd.concat([pd.read_csv(f, header=None) for f in arquivos_ns], ignore_index=True)    # junta os dias
ns.columns = colunas_ns                          # da nome as colunas
print('Ruido: %d janelas em %d dias | janelas com algum NaN (HHE congelado): %d' % (
    len(ns), len(arquivos_ns), ns.isna().any(axis=1).sum()))
if N_RUIDO and len(ns) > N_RUIDO:                # se ha mais ruido que o pedido...
    ns = ns.sample(N_RUIDO, random_state=30002).reset_index(drop=True)   # ...sorteia N_RUIDO janelas
elif N_RUIDO and len(ns) < N_RUIDO:              # se ha menos que o baseline, avisa
    print('ATENCAO: so %d janelas de ruido, abaixo das %d do baseline do Pablo' % (len(ns), N_RUIDO))
ns['evento'] = 'ruido'                           # identificador (para a separacao treino/teste)

# As 140 features = colunas do ruido, menos as 3 finais (pb_inst, station, y_label)
features = [c for c in colunas_ns if c not in ('pb_inst', 'station', 'y_label')]
assert len(features) == 140 and all(f in eq.columns for f in features), 'as colunas de features nao batem'
if SO_NZ:                                        # versao so com N e Z:
    features = [f for f in features if f.startswith(('N_', 'Z_'))]   # fica so com as features N_ e Z_ (90)
    print('Usando so os componentes N e Z: %d features' % len(features))

# === 3. Teste 90/10 (opcional) ===
if '--sem-teste' not in sys.argv:
    rng = np.random.default_rng(30002)           # sorteio reproduzivel
    eventos = eq.evento.unique()                 # lista de terremotos
    ev_teste = set(rng.choice(eventos, size=len(eventos) // 10, replace=False))   # 10 % dos terremotos
    eq_teste = eq[eq.evento.isin(ev_teste)]      # janelas desses terremotos -> teste
    eq_treino = eq[~eq.evento.isin(ev_teste)]    # o resto -> treino
    ns_teste = ns.sample(frac=0.1, random_state=1)   # 10 % do ruido -> teste
    ns_treino = ns.drop(ns_teste.index)          # o resto -> treino
    treino = pd.concat([eq_treino[features + ['y_label']], ns_treino[features + ['y_label']]])   # junta
    teste = pd.concat([eq_teste[features + ['y_label']], ns_teste[features + ['y_label']]])
    print('\n--- Teste: treino com %d janelas, teste com %d ---' % (len(treino), len(teste)))
    m = novo_modelo()                            # modelo novo
    t = time.time()                              # cronometro
    m.fit(treino[features].values, treino['y_label'].values.astype(int))   # TREINA
    print('treino levou %.1f min' % ((time.time() - t) / 60))
    prob = m.predict_proba(teste[features].values)   # probabilidades N/P/S de cada janela de teste
    previsto = prob.argmax(axis=1)               # a classe com maior probabilidade
    verdade = teste['y_label'].values.astype(int)    # a classe verdadeira
    print('Matriz de confusao (linhas = verdade N/P/S; colunas = previsto N/P/S):')
    print(confusion_matrix(verdade, previsto))
    print(classification_report(verdade, previsto, target_names=['ruido', 'P', 'S'], digits=4))
    congelado = ns_teste[features].isna().any(axis=1).values   # janelas de ruido com NaN = HHE congelado
    p_ruido = prob[len(eq_teste):, 1]            # prob. de P das janelas de ruido (vem depois dos terremotos no teste)
    for limiar in (0.8, 0.9, 0.95):              # para cada limiar de disparo...
        print('P >= %.2f: acerta %.1f%% das janelas P | ruido que vira P: %.4f%% (HHE congelado %.4f%%, normal %.4f%%)' % (
            limiar, 100 * (prob[verdade == 1, 1] >= limiar).mean(), 100 * (p_ruido >= limiar).mean(),
            100 * (p_ruido[congelado] >= limiar).mean() if congelado.any() else float('nan'),
            100 * (p_ruido[~congelado] >= limiar).mean()))

# === 4. Modelo final, com todos os dados ===
dados = pd.concat([eq[features + ['y_label']], ns[features + ['y_label']]])   # terremotos + ruido
print('\n--- Modelo final: %d janelas (ruido/P/S = %s) ---' % (len(dados), np.bincount(dados.y_label.astype(int)).tolist()))
m = novo_modelo()                                # modelo novo
t = time.time()                                  # cronometro
m.fit(dados[features].values, dados['y_label'].values.astype(int))   # TREINA com tudo
print('treino levou %.1f min' % ((time.time() - t) / 60))
os.makedirs(os.path.join(PASTA, 'saved_models'), exist_ok=True)   # cria a pasta de modelos
nome = os.path.join(PASTA, 'saved_models', 'DET_ISPT%s_Whole_XGB_10tp3.0to3.0each0.5f7_unbalanced_official_v16.joblib'
                    % ('_NZ' if SO_NZ else ''))   # o modelo NZ ganha "_NZ" no nome
joblib.dump(m, open(nome, 'wb'), compress=3)     # salva o modelo (compactado)
print('Modelo salvo em %s | tempo total %.1f min' % (nome, (time.time() - inicio) / 60))
