import time, threading, math, csv
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
import pynvml as nvml
import matplotlib.pyplot as plt

SAMPLE_MS = 50
DURATION_S = 10
GPU_INDEX = 0

nvml.nvmlInit()
h = nvml.nvmlDeviceGetHandleByIndex(GPU_INDEX)
rx = nvml.NVML_PCIE_UTIL_RX_BYTES
tx = nvml.NVML_PCIE_UTIL_TX_BYTES

ts, sm, mem, vram, rx_kbs, tx_kbs = [], [], [], [], [], []
start = time.time()
stop = False

def poll():
    def get_util():
        return nvml.nvmlDeviceGetUtilizationRates(h)

    def get_mem():
        return nvml.nvmlDeviceGetMemoryInfo(h)

    def get_pcie():
        try:
            r = nvml.nvmlDeviceGetPcieThroughput(h, rx)  # KB/s
            w = nvml.nvmlDeviceGetPcieThroughput(h, tx)
        except nvml.NVMLError:
            r = w = 0
        return r, w

    while not stop:
        with ThreadPoolExecutor(max_workers=4) as ex:
            fu = ex.submit(get_util)
            fm = ex.submit(get_mem)
            fp = ex.submit(get_pcie)
            fs = ex.submit(time.sleep, SAMPLE_MS/1000.0)
            wait([fu, fm, fp, fs], return_when=ALL_COMPLETED)
        # After all 4 complete, record a sample
        t = (time.time()-start)*1000.0
        u = fu.result()
        m = fm.result()
        r, w = fp.result()
        ts.append(t); sm.append(u.gpu); mem.append(u.memory); vram.append(m.used/1e6); rx_kbs.append(r); tx_kbs.append(w)

thr = threading.Thread(target=poll, daemon=True); thr.start()
# ... run your Spark action here ...
time.sleep(DURATION_S)  # or join on your job
stop = True; thr.join()

# Write CSV: one row per datapoint
out_csv = "gpu_utilization.csv"
with open(out_csv, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["ms", "sm_util_pct", "mem_util_pct", "vram_used_mb", "pcie_rx_kbs", "pcie_tx_kbs"])
    for i in range(len(ts)):
        w.writerow([f"{ts[i]:.3f}", sm[i], mem[i], f"{vram[i]:.3f}", rx_kbs[i], tx_kbs[i]])

fig, ax = plt.subplots(1,1, figsize=(10,4))
ax.plot(ts, sm, label='SM %')
ax.plot(ts, mem, label='Mem %')
ax.plot(ts, vram, label='VRAM MB')
ax.plot(ts, rx_kbs, label='PCIe RX KB/s')
ax.plot(ts, tx_kbs, label='PCIe TX KB/s')
ax.set_xlabel('ms')
ax.set_ylabel('value (mixed units)')
ax.legend(loc='best', ncol=3)
plt.tight_layout()
fig.savefig("gpu_utilization.pdf", bbox_inches='tight')
plt.show()