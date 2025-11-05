import time, threading, math, csv, os
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
try:
    import pynvml as nvml  # GPU metrics (optional when CPU_ONLY)
except Exception:
    nvml = None
import psutil
import matplotlib.pyplot as plt

SAMPLE_MS = 50
DURATION_S = 140
GPU_INDEX = 0

def _as_bool_env(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def collect_utilization(sample_ms=SAMPLE_MS, duration_s=DURATION_S, gpu_index=GPU_INDEX, cpu_only: Optional[bool] = None):
    # Determine mode: prefer explicit arg, else env CPU_ONLY
    if cpu_only is None:
        cpu_only = _as_bool_env("CPU_ONLY", False)

    if not cpu_only and nvml is not None:
        nvml.nvmlInit()
        h = nvml.nvmlDeviceGetHandleByIndex(gpu_index)
        rx = nvml.NVML_PCIE_UTIL_RX_BYTES
        tx = nvml.NVML_PCIE_UTIL_TX_BYTES
    else:
        h = None
        rx = tx = None

    ts, sm, mem, cpu, vram, rx_kbs, tx_kbs = [], [], [], [], [], [], []
    start = time.time()
    stop = False

    def poll():
        def get_util():
            if cpu_only or nvml is None or h is None:
                class U:  # minimal duck type for nvmlUtilRates
                    gpu = 0
                    memory = 0
                return U()
            return nvml.nvmlDeviceGetUtilizationRates(h)

        def get_mem():
            if cpu_only or nvml is None or h is None:
                class M:
                    used = 0
                return M()
            return nvml.nvmlDeviceGetMemoryInfo(h)

        def get_pcie():
            if cpu_only or nvml is None or h is None:
                return 0, 0
            try:
                r = nvml.nvmlDeviceGetPcieThroughput(h, rx)  # KB/s
                w = nvml.nvmlDeviceGetPcieThroughput(h, tx)
            except Exception:
                r = w = 0
            return r, w

        def get_cpu():
            # Non-blocking instantaneous CPU% since last call
            return psutil.cpu_percent(None)

    # Warm up interval so NVML has a sampling window before first read
        # Prime psutil baseline to avoid initial 0.0 reading
        try:
            psutil.cpu_percent(None)
        except Exception:
            pass
        time.sleep(sample_ms/1000.0)
        while not stop:
            time.sleep(sample_ms/1000.0)
            with ThreadPoolExecutor(max_workers=4) as ex:
                fu = ex.submit(get_util)
                fm = ex.submit(get_mem)
                fp = ex.submit(get_pcie)
                fc = ex.submit(get_cpu)
                wait([fu, fm, fp, fc], return_when=ALL_COMPLETED)
            # After all complete, record a sample taken for this interval
            t = (time.time()-start)*1000.0
            u = fu.result()
            m = fm.result()
            r, w = fp.result()
            c = fc.result()
            ts.append(t); sm.append(u.gpu); mem.append(u.memory); cpu.append(c); vram.append(m.used/1e6); rx_kbs.append(r); tx_kbs.append(w)

    thr = threading.Thread(target=poll, daemon=True)
    thr.start()
    time.sleep(duration_s)
    stop = True
    thr.join()
    return ts, sm, mem, cpu, vram, rx_kbs, tx_kbs

# --- Utilities to store and plot ---
def write_csv(ts, sm, mem, cpu, vram, rx_kbs, tx_kbs, out_csv):
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ms", "sm_util_pct", "mem_util_pct", "cpu_util_pct", "vram_used_mb", "pcie_rx_kbs", "pcie_tx_kbs"])
        for i in range(len(ts)):
            w.writerow([f"{ts[i]:.3f}", sm[i], mem[i], cpu[i], f"{vram[i]:.3f}", rx_kbs[i], tx_kbs[i]])
    return out_csv

def plot_from_csv(path_name):
    t, sm_u, mem_u, cpu_u, vram_mb, rx, tx = [], [], [], [], [], [], []
    with open(path_name+".csv", "r") as f:
        r = csv.reader(f)
        header = next(r, None)
        for row in r:
            if len(row) < 6:
                continue
            t.append(float(row[0]))
            sm_u.append(float(row[1]))
            mem_u.append(float(row[2]))
            if len(row) >= 7:
                cpu_u.append(float(row[3]))
                vram_mb.append(float(row[4]))
                rx.append(float(row[5]))
                tx.append(float(row[6]))
            else:
                cpu_u.append(0.0)
                vram_mb.append(float(row[3]))
                rx.append(float(row[4]))
                tx.append(float(row[5]))
    fig, ax = plt.subplots(2,1, figsize=(10,5), sharex=True)
    ax[0].plot(t, sm_u, label='SM %'); ax[0].plot(t, mem_u, label='Mem %'); ax[0].plot(t, cpu_u, label='CPU %')
    ax[0].legend(); ax[0].set_ylabel('%')
    # ax[1].plot(t, vram_mb, label='VRAM MB')
    # ax[1].legend(); ax[1].set_ylabel('MB')
    ax[1].plot(t, rx, label='PCIe RX KB/s'); ax[1].plot(t, tx, label='PCIe TX KB/s')
    ax[1].legend(); ax[1].set_ylabel('KB/s'); ax[1].set_xlabel('ms')
    plt.tight_layout()
    fig.savefig(path_name+".pdf", bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    cpu_only = _as_bool_env("CPU_ONLY", False)
    if cpu_only:
        path_name = "cpu_utilization"
    else:
        path_name = "gpu_utilization"
    ts, sm, mem, cpu, vram, rx_kbs, tx_kbs = collect_utilization()
    write_csv(ts, sm, mem, cpu, vram, rx_kbs, tx_kbs, out_csv=path_name+".csv")
    plot_from_csv(path_name)