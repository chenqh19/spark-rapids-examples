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

# install openjdk-17-jdk
sudo apt update
sudo apt install -y build-essential git cmake ninja-build ccache pkg-config \
  openjdk-17-jdk curl wget unzip zip

# install maven
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk install maven 3.9.6
mvn -v

# check ubuntu version
lsb_release -a

sudo apt update
sudo apt install -y build-essential dkms linux-headers-$(uname -r) \
    software-properties-common pciutils

# install nvidia driver
sudo apt install -y nvidia-driver-570-server nvidia-utils-570-server

wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get install -y cuda-toolkit-12-9

echo 'export PATH=/usr/local/cuda-12.9/bin:$PATH' | sudo tee /etc/profile.d/cuda.sh
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.9/lib64:$LD_LIBRARY_PATH' | sudo tee -a /etc/profile.d/cuda.sh
source /etc/profile.d/cuda.sh

nvidia-smi
nvcc --version


# install cuda 12.9
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit-12-9

echo 'export PATH=/usr/local/cuda-12.9/bin:$PATH' | sudo tee /etc/profile.d/cuda.sh
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.9/lib64:$LD_LIBRARY_PATH' | sudo tee -a /etc/profile.d/cuda.sh
source /etc/profile.d/cuda.sh

nvcc --version

# install spark
cd $HOME && git clone https://github.com/apache/spark.git
cd spark && git checkout v3.5.6
git clean -xfd
rm -rf ~/.m2/repository/org/apache/spark

./dev/make-distribution.sh \
  --name nocuda \
  -Phadoop-3 -Pscala-2.12 \
  -DskipTests -Dmaven.test.skip=true

# build distribution incl. Hive & ThriftServer (still skipping tests)
# ./dev/make-distribution.sh \
#   --name withhive \
#   -Phadoop-3 -Pscala-2.12 -Phive -Phive-thriftserver \
#   -DskipTests -Dmaven.test.skip=true


ls -lh ./dist

export SPARK_HOME="$HOME/spark/dist"
[ -x "$SPARK_HOME/bin/spark-shell" ] && echo "OK: $SPARK_HOME" || echo "BAD path"

echo 'export SPARK_HOME="$HOME/spark/dist"' >> ~/.bashrc
echo 'export PATH="$SPARK_HOME/bin:$PATH"'  >> ~/.bashrc
source ~/.bashrc
# check spark
"$SPARK_HOME/bin/spark-submit" --version
"$SPARK_HOME/bin/spark-shell"  --version
cat "$SPARK_HOME/RELEASE"
"$SPARK_HOME/bin/run-example" SparkPi 1000



export RAPIDS_VER=25.08.0
export SCALA_BIN=2.12          
export SPARK_HOME="$HOME/spark/dist"
mkdir -p "$SPARK_HOME/jars/rapids"

mvn -B -U dependency:get -Dartifact=com.nvidia:rapids-4-spark_${SCALA_BIN}:${RAPIDS_VER}
mvn -B -U dependency:get -Dartifact=com.nvidia:spark-rapids-jni:${RAPIDS_VER}
mvn -B -U dependency:get -Dartifact=ai.rapids:cudf:${RAPIDS_VER}

cp ~/.m2/repository/com/nvidia/rapids-4-spark_${SCALA_BIN}/${RAPIDS_VER}/rapids-4-spark_${SCALA_BIN}-${RAPIDS_VER}.jar \
   "$SPARK_HOME/jars/rapids/"
cp ~/.m2/repository/com/nvidia/spark-rapids-jni/${RAPIDS_VER}/spark-rapids-jni-${RAPIDS_VER}.jar \
   "$SPARK_HOME/jars/rapids/"
cp ~/.m2/repository/ai/rapids/cudf/${RAPIDS_VER}/cudf-${RAPIDS_VER}.jar \
   "$SPARK_HOME/jars/rapids/"

mv "$SPARK_HOME/jars/rapids/"*.jar "$SPARK_HOME/jars/"


ls -lh "$SPARK_HOME/jars/"

# check RAPIDS
"$SPARK_HOME/bin/spark-shell" --master local[1] \
  --conf spark.plugins=com.nvidia.spark.SQLPlugin \
  --conf spark.rapids.sql.enabled=true \
  --conf spark.rapids.sql.explain=ALL \
  --conf spark.rapids.sql.allowMultipleJars=ALWAYS \
  --conf spark.executor.extraLibraryPath=/usr/local/cuda-12.9/lib64 \
  --conf spark.driver.extraLibraryPath=/usr/local/cuda-12.9/lib64 \
  -i <(cat <<'SCALA'
val df = spark.range(0, 20000000).selectExpr("id","id % 10 AS g")
println("GPU running... " + df.groupBy("g").count().collect().mkString(","))
System.exit(0)
SCALA
)


