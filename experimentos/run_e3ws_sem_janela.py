"""Roda real_time/E3WS_rt.py sem abrir janela de grafico.

O plt.show() do script original e trocado por plt.savefig(), e a figura
vai para real_time/results/E3WS_plot_N.png. O script do autor nao e alterado.

Uso (a partir da pasta real_time, com o ambiente E3WS ativo):
    cd real_time
    python ../experimentos/run_e3ws_sem_janela.py
"""
import sys, os, runpy, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
n = [0]
def _show(*a, **k):
    n[0] += 1
    out = os.path.join("results", "E3WS_plot_%d.png" % n[0])
    plt.savefig(out, dpi=120, bbox_inches="tight"); print("FIGURA SALVA:", out)
plt.show = _show
sys.path.insert(0, os.getcwd())
runpy.run_path("E3WS_rt.py", run_name="__main__")
