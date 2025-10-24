wget https://www.mellanox.com/downloads/DOCA/DOCA_v3.1.0/host/doca-host_3.1.0-091000-25.07-ubuntu2004_amd64.deb
sudo dpkg -i doca-host_3.1.0-091000-25.07-ubuntu2004_amd64.deb
sudo apt-get update
sudo apt-get install -y doca-runtime doca-sdk doca-tools

sudo systemctl enable --now rshim
sudo ip addr add 192.168.100.1/24 dev tmfifo_net0 || true
ping -c1 192.168.100.2

# password: ubuntu
openssl passwd -1
# copy the output, e.g. $1$3B0R...$TlHr...
echo "ubuntu_PASSWORD='$1$3B0R...$TlHr...'" > bf.cfg

sudo bfb-install --rshim rshim0 --bfb bf-bundle-3.1.0-76_25.07_ubuntu-22.04_prod.bfb --config bf.cfg

sudo ifconfig tmfifo_net0 192.168.100.1/24
ssh ubuntu@192.168.100.2 # password: chenqh23chenqh23