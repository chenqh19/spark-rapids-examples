import time, threading, math, csv
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
import pynvml as nvml
import matplotlib.pyplot as plt

SAMPLE_MS = 50
DURATION_S = 70
GPU_INDEX = 0

def collect_utilization(sample_ms=SAMPLE_MS, duration_s=DURATION_S, gpu_index=GPU_INDEX):
    nvml.nvmlInit()
    h = nvml.nvmlDeviceGetHandleByIndex(gpu_index)
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

    # Warm up interval so NVML has a sampling window before first read
        time.sleep(sample_ms/1000.0)
        while not stop:
            time.sleep(sample_ms/1000.0)
            with ThreadPoolExecutor(max_workers=3) as ex:
                fu = ex.submit(get_util)
                fm = ex.submit(get_mem)
                fp = ex.submit(get_pcie)
                wait([fu, fm, fp], return_when=ALL_COMPLETED)
            # After all complete, record a sample taken for this interval
            t = (time.time()-start)*1000.0
            u = fu.result()
            m = fm.result()
            r, w = fp.result()
            ts.append(t); sm.append(u.gpu); mem.append(u.memory); vram.append(m.used/1e6); rx_kbs.append(r); tx_kbs.append(w)

    thr = threading.Thread(target=poll, daemon=True)
    thr.start()
    time.sleep(duration_s)
    stop = True
    thr.join()
    return ts, sm, mem, vram, rx_kbs, tx_kbs

# --- Utilities to store and plot ---
def write_csv(ts, sm, mem, vram, rx_kbs, tx_kbs, out_csv="gpu_utilization.csv"):
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ms", "sm_util_pct", "mem_util_pct", "vram_used_mb", "pcie_rx_kbs", "pcie_tx_kbs"])
        for i in range(len(ts)):
            w.writerow([f"{ts[i]:.3f}", sm[i], mem[i], f"{vram[i]:.3f}", rx_kbs[i], tx_kbs[i]])
    return out_csv

def plot_from_csv(csv_path, pdf_path="gpu_utilization.pdf"):
    t, sm_u, mem_u, vram_mb, rx, tx = [], [], [], [], [], []
    with open(csv_path, "r") as f:
        r = csv.reader(f)
        header = next(r, None)
        for row in r:
            if len(row) < 6:
                continue
            t.append(float(row[0]))
            sm_u.append(float(row[1]))
            mem_u.append(float(row[2]))
            vram_mb.append(float(row[3]))
            rx.append(float(row[4]))
            tx.append(float(row[5]))
    fig, ax = plt.subplots(2,1, figsize=(10,5), sharex=True)
    ax[0].plot(t, sm_u, label='SM %'); ax[0].plot(t, mem_u, label='Mem %')
    ax[0].legend(); ax[0].set_ylabel('%')
    # ax[1].plot(t, vram_mb, label='VRAM MB')
    # ax[1].legend(); ax[1].set_ylabel('MB')
    ax[1].plot(t, rx, label='PCIe RX KB/s'); ax[1].plot(t, tx, label='PCIe TX KB/s')
    ax[1].legend(); ax[1].set_ylabel('KB/s'); ax[1].set_xlabel('ms')
    plt.tight_layout()
    fig.savefig(pdf_path, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    csv_path = "gpu_utilization.csv"
    # ts, sm, mem, vram, rx_kbs, tx_kbs = collect_utilization()
    # write_csv(ts, sm, mem, vram, rx_kbs, tx_kbs, csv_path)
    plot_from_csv(csv_path)