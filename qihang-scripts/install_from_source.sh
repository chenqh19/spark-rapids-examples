# install cudf
cd $HOME
wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh -b -p $HOME/miniforge
source "$HOME/miniforge/etc/profile.d/conda.sh"
conda create -n cudf-build -y python=3.10
conda activate cudf-build
conda install -y -c conda-forge -c nvidia \
  cmake ninja ccache gxx_linux-64=12 make pkg-config \
  boost-cpp gtest \
  ucx ucx-proc=*=gpu \
  cuda-version=12.9 cuda-nvcc cuda-profiler-api
conda install -y -c conda-forge zlib lz4-c zstd snappy brotli libiconv
conda install -y -c nvidia -c conda-forge \
  cuda-nvrtc=12.9 cuda-nvrtc-dev=12.9
export ZLIB_ROOT="$CONDA_PREFIX"
export CMAKE_PREFIX_PATH="$CONDA_PREFIX:$CMAKE_PREFIX_PATH"
git clone https://github.com/rapidsai/cudf.git
cd cudf && git checkout branch-25.08
export CMAKE_CUDA_ARCHITECTURES=80
export PARALLEL_LEVEL=$(nproc)
rm -rf cpp/build
cmake -S cpp -B cpp/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CUDA_ARCHITECTURES=80 \
  -DCMAKE_PREFIX_PATH="$CONDA_PREFIX" \
  -DZLIB_ROOT="$CONDA_PREFIX" \
  -DCMAKE_CXX_FLAGS="-Wno-error"
cmake --build cpp/build --verbose
./build.sh java -v |& tee build_java.log
cd java
mvn -B -DskipTests install
cd java && mvn -B -DskipTests install

export RAPIDS_REL=25.08.0
export CUDA_VER=12.9
export SPARK_VER=3.5.6
export BUILDVER=350
export CMAKE_CUDA_ARCHITECTURES=80

# update cmake
sudo apt-get remove -y cmake || true
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates gnupg curl
sudo curl -fsSL https://apt.kitware.com/kitware-archive.sh | sudo bash
sudo apt-get update
sudo apt-get install -y cmake
cmake --version

cd ~
git clone https://github.com/NVIDIA/spark-rapids-jni.git
cd spark-rapids-jni
git checkout branch-${RAPIDS_REL%.*}
git submodule sync --recursive
git submodule update --init --recursive --jobs 8
git submodule foreach --recursive 'git reset --hard'
git submodule foreach --recursive 'git clean -xfd'
git submodule update --init --recursive --jobs 8
git config --global submodule.recurse true

mvn -B -DskipTests \
  -Dcuda.version=${CUDA_VER} \
  -Dcmake.cuda.arch=${CMAKE_CUDA_ARCHITECTURES} \
  -Dcudf.version=${RAPIDS_REL} \
  clean install

cd ~
git clone https://github.com/NVIDIA/spark-rapids.git
cd spark-rapids
git checkout branch-${RAPIDS_REL%.*}

mvn -B -DskipTests -Dbuildver=${BUILDVER} clean package