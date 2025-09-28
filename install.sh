export CUDA_VER=12.9
export RAPIDS_REL=25.08.0        
export SPARK_VER=3.5.6
export SCALA_BIN=2.12             
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export NPROC=$(nproc)

sudo apt-get update
sudo apt install -y build-essential dkms linux-headers-$(uname -r) \
    software-properties-common pciutils
# sudo apt-get install -y build-essential git curl wget cmake ninja-build ccache \
#     pkg-config autoconf libtool unzip zip software-properties-common

# Java 17 + Maven 3.9（Ubuntu 22.04 自带 3.6/3.8，自己装更稳）
sudo apt-get install -y openjdk-17-jdk
wget -qO- https://downloads.apache.org/maven/maven-3/3.9.6/binaries/apache-maven-3.9.6-bin.tar.gz \
 | sudo tar -xz -C /opt
sudo ln -sf /opt/apache-maven-3.9.6/bin/mvn /usr/local/bin/mvn

# （可选）NVIDIA 驱动（如已有可跳过）
sudo add-apt-repository -y ppa:graphics-drivers/ppa
sudo apt-get update && sudo apt-get install -y nvidia-driver-555

# CUDA 12.9 工具链（官方 keyring 仓库）
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get install -y cuda-toolkit-12-9
echo 'export PATH=/usr/local/cuda-12.9/bin:$PATH' | sudo tee /etc/profile.d/cuda.sh
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.9/lib64:$LD_LIBRARY_PATH' | sudo tee -a /etc/profile.d/cuda.sh
source /etc/profile.d/cuda.sh

# 验证 GPU/CUDA
nvidia-smi
nvcc --version

wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit-12-9

echo 'export PATH=/usr/local/cuda-12.9/bin:$PATH' | sudo tee /etc/profile.d/cuda.sh
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.9/lib64:$LD_LIBRARY_PATH' | sudo tee -a /etc/profile.d/cuda.sh
source /etc/profile.d/cuda.sh

nvcc --version