import pynvml, time

PCIe_THEO = {
    1: {1: 0.25, 4: 1.0, 8: 2.0, 16: 4.0},       # Gen1 estimated
    2: {1: 0.5,  4: 2.0, 8: 4.0, 16: 8.0},       # Gen2 estimated
    3: {1: 0.985,4: 3.94,8: 7.88,16: 15.75},     # Gen3 estimated
    4: {1: 1.97, 4: 7.88,8: 15.75,16: 31.5},     # Gen4 estimated
    5: {1: 3.94, 4: 15.75,8: 31.5,16: 63.0},     # Gen5 estimated
}

pynvml.nvmlInit()
h = pynvml.nvmlDeviceGetHandleByIndex(0)

gen  = pynvml.nvmlDeviceGetCurrPcieLinkGeneration(h)
width = pynvml.nvmlDeviceGetCurrPcieLinkWidth(h)

theo_gbps = PCIe_THEO.get(gen, {}).get(width, None)  # single direction limit (GB/s)

print(f"PCIe Gen{gen} x{width}, theoretical ~{theo_gbps} GB/s per direction")

while True:
    rx_kbs = pynvml.nvmlDeviceGetPcieThroughput(h, pynvml.NVML_PCIE_UTIL_RX_BYTES)  # host->GPU
    tx_kbs = pynvml.nvmlDeviceGetPcieThroughput(h, pynvml.NVML_PCIE_UTIL_TX_BYTES)  # GPU->host
    rx_gbs = rx_kbs / 1e6
    tx_gbs = tx_kbs / 1e6
    if theo_gbps:
        rx_pct = 100 * rx_gbs / theo_gbps
        tx_pct = 100 * tx_gbs / theo_gbps
        print(f"RX {rx_gbs:.3f} GB/s ({rx_pct:.1f}%), TX {tx_gbs:.3f} GB/s ({tx_pct:.1f}%)")
    else:
        print(f"RX {rx_gbs:.3f} GB/s, TX {tx_gbs:.3f} GB/s")
    time.sleep(0.5)
