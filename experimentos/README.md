# Experimentos com o E3WS

Registro dos testes feitos com o E3WS (fork de [PabloELara/E3WS](https://github.com/PabloELara/E3WS)).
Código e modelos são de Pablo Lara et al. (2023), licença CC BY 4.0.

## Ambiente

- Windows 11, Miniconda, ambiente `E3WS` com Python 3.9.23
- Versões do README do autor: `xgboost==1.6.1`, `scikit-learn==1.1.1`, `scipy==1.8.1`,
  `obspy==1.3.0`, `python-speech-features==0.6`, `PyGeodesy==23.3.23`
- Também: `numpy==1.22.4`, `matplotlib==3.5.3`, `joblib`

```
conda create -n E3WS --override-channels -c conda-forge python=3.9 pip
conda activate E3WS
pip install --only-binary=:all: --no-binary=python-speech-features numpy==1.22.4 scipy==1.8.1 xgboost==1.6.1 scikit-learn==1.1.1 obspy==1.3.0 python-speech-features==0.6 PyGeodesy==23.3.23 matplotlib==3.5.3 joblib
```

Se o pip falhar com `CERTIFICATE_VERIFY_FAILED` (antivírus ou proxy interceptando HTTPS),
acrescente `--use-feature=truststore`.

## Modelos baixados

O repositório completo tem 8,3 GB. Para os testes, só parte dos modelos foi baixada com
sparse checkout:

```bash
git clone --filter=blob:none --no-checkout --depth 1 https://github.com/rickalves/E3WS.git
cd E3WS
git sparse-checkout set --no-cone '/*' '!/models/*' '/models/PICK/*' '/models/DET/DET_SLRZ_*' \
  '/models/MAG/*7tp[3-7]f45*' '/models/DIS/*7tp[3-7]f45*' '/models/DEP/*7tp[3-7]f45*' '/models/BAZ/*7tp3f45*'
git checkout experimentos
```

## Como rodar

```
conda activate E3WS
cd real_time
python E3WS_rt.py                                 # abre o gráfico numa janela
python ../experimentos/run_e3ws_sem_janela.py     # salva o gráfico em results/ (sem janela)
```

O script sobrescreve `real_time/results/SLRZ_Canta_M5.6_20220107.csv`, que é o resultado de
referência do autor. Depois de cada experimento, copie a saída para a pasta do experimento e
restaure o original com `git checkout -- real_time/results/SLRZ_Canta_M5.6_20220107.csv`.

## Experimentos

| # | Data | O que mudou | Mag. 3 s | Mag. final | Dist. final (km) | BAZ final (°) | Conclusão |
|---|---|---|---|---|---|---|---|
| [01](exp01_teste_inicial/) | 2026-11-15 | Nada (configuração padrão) | 5,34 | 5,49 (7 s) | 66,0 | −124,3 | Reproduz a referência do autor |

Evento de teste: Canta, M5,6, 07/01/2022, estação SLRZ (Lima, Peru).
