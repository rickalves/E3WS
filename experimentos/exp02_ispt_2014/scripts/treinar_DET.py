"""Treina o detector (DET) do E3WS para a estacao ISPT.

Segue o pb_save_trainingmodel_official_LOO_Ecuador.py do Pablo:
  - terremotos: atr_eq DET_7.00tp3.00 (janelas com P ou S 3 s antes do fim);
  - ruido: features da ISPT (treino_DET/atr_noise/ISPT), ate 900 mil janelas;
  - classes: 0 = ruido, 1 = P, 2 = S;
  - modelo: StandardScaler + XGBClassifier (6000 arvores, profundidade 4), na GPU.
Acrescimo: antes do modelo final, treina com 90 % e testa nos 10 % restantes
(separados por terremoto, para o teste ter so eventos nunca vistos).

Uso: python treinar_DET.py <pasta treino_DET> [--cpu] [--sem-teste]
"""
import sys, os, glob, time
import numpy as np, pandas as pd, joblib
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix, classification_report
import xgboost as xgb

np.random.seed(30002)
PASTA = sys.argv[1]
TREE = "hist" if "--cpu" in sys.argv else "gpu_hist"
SAMPLES_NOISE = 900000
DEL_COL = ['lambda_2', 'lambda_3', 'E_maxturnpoints_t', 'N_maxturnpoints_t', 'Z_maxturnpoints_t',
           'E_IncDec_t', 'N_IncDec_t', 'Z_IncDec_t', 'E_growth_t', 'N_growth_t', 'Z_growth_t',
           'E_minturnpoints_t', 'N_minturnpoints_t', 'Z_minturnpoints_t',
           'E_maxturnpoints_f', 'N_maxturnpoints_f', 'Z_maxturnpoints_f',
           'E_minturnpoints_f', 'N_minturnpoints_f', 'Z_minturnpoints_f',
           'cov_EN', 'cov_EZ', 'cov_NZ', 'E_Erms_t', 'N_Erms_t', 'Z_Erms_t',
           'E_Etot_f', 'N_Etot_f', 'Z_Etot_f', 'E_Erms_f', 'N_Erms_f', 'Z_Erms_f']


def rotulo(psaft):
    """'P+3.0' -> 1, 'S+3.0' -> 2 (mesma regra do Pablo: >= 0,5 s apos a fase)."""
    fase, t = psaft[0], float(psaft[1:].replace('+-', '-'))
    if fase == 'N' or t < 0.5:
        return 0
    return 1 if fase == 'P' else 2


def modelo():
    return make_pipeline(StandardScaler(), xgb.XGBClassifier(
        tree_method=TREE, colsample_bytree=0.4603, gamma=0.0468, learning_rate=0.05, max_depth=4,
        min_child_weight=1.7817, n_estimators=6000, reg_alpha=0.4640, reg_lambda=0.8571,
        subsample=0.8, verbosity=0, nthread=-1))


t_ini = time.time()
# --- terremotos ---
cols_eq = pd.read_csv(os.path.join(PASTA, 'pb_index_DET_v16.csv')).feature.values
f_eq = glob.glob(os.path.join(PASTA, 'atr_eq', 'DET_*tp*.csv'))
eq = pd.concat([pd.read_csv(f, header=None) for f in f_eq], ignore_index=True)
eq.columns = cols_eq
eq = eq.drop(columns=DEL_COL)
eq = eq[eq['ENZ_equal'] == 'ENZ_different'].reset_index(drop=True)
eq['y_label'] = eq['PSaft'].apply(rotulo)
eq['evento'] = eq['e_mag'].round(2).astype(str) + '_' + eq['eq_lat'].round(3).astype(str) + '_' + eq['eq_lon'].round(3).astype(str)
print('Terremotos: %d janelas, %d eventos, rotulos: %s' % (len(eq), eq.evento.nunique(), eq.PSaft.value_counts().to_dict()))

# --- ruido ---
cols_ns = pd.read_csv(os.path.join(PASTA, 'pb_index_SASPe_official_v16.csv')).feature.values
f_ns = sorted(glob.glob(os.path.join(PASTA, 'atr_noise', 'ISPT', 'DET_*.csv')))
ns = pd.concat([pd.read_csv(f, header=None) for f in f_ns], ignore_index=True)
ns.columns = cols_ns
print('Ruido: %d janelas em %d dias' % (len(ns), len(f_ns)))
if len(ns) > SAMPLES_NOISE:
    ns = ns.sample(SAMPLES_NOISE, random_state=30002).reset_index(drop=True)
ns['evento'] = 'ruido'

feats = [c for c in cols_ns if c not in ('pb_inst', 'station', 'y_label')]
assert len(feats) == 140 and all(f in eq.columns for f in feats), 'colunas de features nao batem'

# --- teste 90/10 ---
if '--sem-teste' not in sys.argv:
    evs = eq.evento.unique(); rng = np.random.default_rng(30002)
    ev_teste = set(rng.choice(evs, size=len(evs) // 10, replace=False))
    eq_te = eq[eq.evento.isin(ev_teste)]; eq_tr = eq[~eq.evento.isin(ev_teste)]
    ns_te = ns.sample(frac=0.1, random_state=1); ns_tr = ns.drop(ns_te.index)
    tr = pd.concat([eq_tr[feats + ['y_label']], ns_tr[feats + ['y_label']]])
    te = pd.concat([eq_te[feats + ['y_label']], ns_te[feats + ['y_label']]])
    print('\nTeste: treino com %d janelas, teste com %d (eventos nunca vistos)' % (len(tr), len(te)))
    m = modelo(); t = time.time(); m.fit(tr[feats].values, tr['y_label'].values.astype(int))
    print('  treino levou %.1f min' % ((time.time() - t) / 60))
    proba = m.predict_proba(te[feats].values); pred = proba.argmax(1)
    y = te['y_label'].values.astype(int)
    print('Matriz de confusao (linhas = verdade N/P/S, colunas = previsto N/P/S):')
    print(confusion_matrix(y, pred))
    print(classification_report(y, pred, target_names=['ruido', 'P', 'S'], digits=4))
    for thr in (0.8, 0.9, 0.95):
        print('  P >= %.2f: acerta %.1f%% das janelas P | %.4f%% das janelas de ruido viram "P"' % (
            thr, 100 * (proba[y == 1, 1] >= thr).mean(), 100 * (proba[y == 0, 1] >= thr).mean()))

# --- modelo final com tudo ---
df = pd.concat([eq[feats + ['y_label']], ns[feats + ['y_label']]])
print('\nModelo final: %d janelas (N/P/S = %s)' % (len(df), np.bincount(df.y_label.astype(int)).tolist()))
m = modelo(); t = time.time(); m.fit(df[feats].values, df['y_label'].values.astype(int))
print('  treino levou %.1f min' % ((time.time() - t) / 60))
os.makedirs(os.path.join(PASTA, 'saved_models'), exist_ok=True)
nome = os.path.join(PASTA, 'saved_models', 'DET_ISPT_Whole_XGB_10tp3.0to3.0each0.5f7_unbalanced_official_v16.joblib')
joblib.dump(m, open(nome, 'wb'), compress=3)
print('Salvo:', nome, '| tempo total %.1f min' % ((time.time() - t_ini) / 60))
