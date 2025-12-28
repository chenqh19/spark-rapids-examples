wget https://www.mellanox.com/downloads/DOCA/DOCA_v3.1.0/host/doca-host_3.1.0-091000-25.07-ubuntu2004_amd64.deb
sudo dpkg -i doca-host_3.1.0-091000-25.07-ubuntu2004_amd64.deb
sudo apt-get update
sudo apt-get install doca-all
sudo /etc/init.d/openibd restart
sudo mst restart

sudo -n apt-get install -y libjson-c-dev
sudo -n apt install meson ninja-build || true

sudo apt-get install -y rshim
sudo systemctl enable --now rshim

# password: ubuntu
HASH=$(openssl passwd -6 'chenqh23chenqh23')
printf "ubuntu_PASSWORD='%s'\n" "$HASH" > bf.cfg
# ### TODO: do on my Mac ###: scp Downloads/bf-bundle-3.1.0-76_25.07_ubuntu-22.04_prod.bfb chenqh23@clgpu020.clemson.cloudlab.us:~

sudo bfb-install --rshim rshim0 --bfb ~/bf-bundle-3.1.0-76_25.07_ubuntu-22.04_prod.bfb --config bf.cfg

sudo ip addr add 192.168.100.1/24 dev tmfifo_net0 || true
ping -c1 192.168.100.2
sudo ifconfig tmfifo_net0 192.168.100.1/24
ssh ubuntu@192.168.100.2 # password: chenqh23chenqh23

sudo modprobe -r mlx5_ib mlx5_core || true
sudo modprobe mlx5_core
sudo modprobe mlx5_ib

# put required packages to smartnic
sudo apt install python3-pip

sudo dpkg --add-architecture arm64
echo 'deb [arch=arm64] http://ports.ubuntu.com/ubuntu-ports jammy main universe' | \
  sudo tee /etc/apt/sources.list.d/jammy-arm64.list
sudo apt-get update
mkdir -p ~/dpu_debs && cd ~/dpu_debs
sudo apt-get download ninja-build:arm64 meson
scp ~/dpu_debs/ninja-build_*arm64.deb ~/dpu_debs/meson_*all.deb ubuntu@192.168.100.2:/tmp/

# dpdk
sudo apt update
sudo apt install -y gcc-aarch64-linux-gnu g++-aarch64-linux-gnu \
  meson ninja-build pkg-config git
cd ~
git clone https://github.com/DPDK/dpdk.git
cd dpdk
scp -r /users/chenqh23/dpdk/ ubuntu@192.168.100.2:~

sudo ln -sf /usr/local/app/dpdk-testpmd /usr/local/bin/dpdk-testpmd
echo 1024 | sudo tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
sudo mkdir -p /mnt/huge
sudo mount -t hugetlbfs -o pagesize=2M nodev /mnt/huge
grep -i Huge /proc/meminfo | egrep 'HugePages_Total|HugePages_Free'

### ON SMARTNIC ###

# dpdk
sudo dpkg -i /tmp/ninja-build_*arm64.deb
sudo dpkg -i /tmp/meson_*all.deb
meson --version && ninja --version

set -e
cd ~/dpdk
git checkout v20.11
rm -rf build
/usr/bin/meson setup ~/dpdk/build --buildtype=release -Ddefault_library=shared -Dibverbs_link=dlopen
unset PYTHONPATH; sudo -E /usr/bin/meson install -C ~/dpdk/build
sudo ldconfig

find /usr/local -maxdepth 5 -name 'librte_*mlx5*' -print
echo 1024 | sudo tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
sudo mkdir -p /mnt/huge && sudo mount -t hugetlbfs -o pagesize=2M nodev /mnt/huge
# test
export MLX5_GLUE_PATH=/usr/local/lib/aarch64-linux-gnu/dpdk/pmds-21.0-glue/librte_common_mlx5_glue.so.21.0
sudo dpdk-testpmd -l 0-1 -n 4 -m 1024 \
  -d /usr/local/lib/aarch64-linux-gnu/dpdk/pmds-21.0/librte_common_mlx5.so \
  -d /usr/local/lib/aarch64-linux-gnu/dpdk/pmds-21.0/librte_net_mlx5.so \
  -d /usr/local/lib/aarch64-linux-gnu/dpdk/pmds-21.0/librte_mempool_ring.so \
  -a 0000:03:00.0 -a 0000:03:00.1 \
  -- --txq=1 --rxq=1 --hairpinq=1 --hairpin-mode=0x01 \
     --forward-mode=hairpin --auto-start --stats-period=2



### FILE COMPRESSION ###
# BOTH sides
cd /opt/mellanox/doca/applications
meson /tmp/build -Denable_all_applications=false -Denable_file_compression=true
ninja -C /tmp/build
cd /tmp/build/file_compression/
# DPU side (first)
./doca_file_compression -p 03:00.0 -r 81:00.0 -f received.txt
# HOST side (second)
echo "Message from host!" > send.txt
./doca_file_compression -p 0000:81:00.0 -f send.txt