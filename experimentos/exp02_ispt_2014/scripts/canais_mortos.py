"""Procura dias em que um componente esta morto (sinal constante) em 2014."""
import obspy, numpy as np, sys, csv
from concurrent.futures import ProcessPoolExecutor
B = r"D:\Downloads\ISPT_DATA_SEISMO\2014\EC\ISPT\{c}.D\EC.ISPT..{c}.D.2014.{d:03d}"
def f(d):
    out = {"dia": d}
    for c in ["HHE", "HHN", "HHZ"]:
        st = obspy.read(B.format(c=c, d=d)); x = np.concatenate([tr.data for tr in st]).astype(float)
        out[c + "_std"] = round(x.std(), 2); out[c + "_distintos"] = int(np.unique(x[:200000]).size)
    return out
if __name__ == "__main__":
    with ProcessPoolExecutor(12) as ex: R = list(ex.map(f, range(1, 366)))
    with open(sys.argv[1], "w", newline="") as fh:
        w = csv.DictWriter(fh, R[0].keys()); w.writeheader(); w.writerows(R)
    for c in ["HHE", "HHN", "HHZ"]:
        v = [r["dia"] for r in R if r[c + "_distintos"] < 5]
        print(c, "dias mortos:", len(v), (v[0], v[-1]) if v else "")
    print("dia 60:", R[59]); print("dia 189:", R[188]); print("dia 190:", R[189])
