"""Cobertura diaria dos dados ISPT 2014 (le so cabecalhos)."""
import obspy, glob, os, sys, csv
from concurrent.futures import ProcessPoolExecutor
BASE = sys.argv[1]; OUT = sys.argv[2]
def info(f):
    st = obspy.read(f, headonly=True)
    secs = sum(tr.stats.npts / tr.stats.sampling_rate for tr in st)
    return dict(arquivo=os.path.basename(f), canal=st[0].stats.channel, dia=int(f[-3:]),
                n_traces=len(st), horas=round(secs / 3600, 3), fs=st[0].stats.sampling_rate,
                loc=st[0].stats.location, inicio=str(min(t.stats.starttime for t in st)))
if __name__ == "__main__":
    fs = sorted(glob.glob(os.path.join(BASE, "HH?.D", "*")))
    with ProcessPoolExecutor(12) as ex: rows = list(ex.map(info, fs, chunksize=8))
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, rows[0].keys()); w.writeheader(); w.writerows(rows)
    import collections
    print("taxas:", collections.Counter(r["fs"] for r in rows), "loc:", collections.Counter(r["loc"] for r in rows))
    for ch in ["HHE", "HHN", "HHZ"]:
        h = [r["horas"] for r in rows if r["canal"] == ch]
        print(ch, "horas totais %.0f de 8760 (%.1f%%); dias <23h: %d; dias com >1 trace: %d" % (
            sum(h), 100 * sum(h) / 8760, sum(x < 23 for x in h),
            sum(r["n_traces"] > 1 for r in rows if r["canal"] == ch)))
    bad = [(r["canal"], r["dia"], r["horas"]) for r in rows if r["horas"] < 23]
    print("dias incompletos:", bad[:40])
