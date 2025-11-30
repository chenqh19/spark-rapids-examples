wget https://www.mellanox.com/downloads/DOCA/DOCA_v3.1.0/host/doca-host_3.1.0-091000-25.07-ubuntu2004_amd64.deb
sudo dpkg -i doca-host_3.1.0-091000-25.07-ubuntu2004_amd64.deb
sudo apt-get update
sudo apt-get install -y doca-runtime doca-sdk doca-tools
sudo -n apt-get install -y doca-cx-runtime doca-cx-tools || true
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
mkdir -p ~/bf_wheels
sudo apt install python3-pip
pip3 download \
  --dest ~/bf_wheels \
  --only-binary=:all: \
  --implementation cp \
  --platform manylinux2014_aarch64 \
  --python-version 310 \
  meson ninja
sudo dpkg --add-architecture arm64
echo "deb [arch=arm64] http://ports.ubuntu.com/ubuntu-ports jammy main universe" | \
    sudo tee /etc/apt/sources.list.d/jammy-arm64.list
sudo apt-get update
sudo apt-get download libjson-c-dev:arm64 libjson-c5:arm64
scp libjson-c5_*arm64.deb libjson-c-dev_*arm64.deb ubuntu@192.168.100.2:/tmp/

scp -r ~/bf_wheels ubuntu@192.168.100.2:/tmp/wheels # mkdir -p /tmp/wheels/ on smartnic first

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
set -e
cd ~/dpdk
git checkout v20.11
rm -rf build
meson setup --wipe build
meson setup build --buildtype=release -Dibverbs_link=dlopen
ninja -C build 


# doca
python3 -m ensurepip --upgrade || true
python3 -m pip install --no-index --find-links /tmp/wheels meson ninja
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
. ~/.bashrc
meson --version
ninja --version
sudo dpkg -i /tmp/libjson-c5_*arm64.deb /tmp/libjson-c-dev_*arm64.deb || sudo apt-get -f install