#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
trap 'echo "Error on line $LINENO: $BASH_COMMAND" >&2' ERR

export PS4='[[Running command]] '
set -x

export CUDA_VER=12.9
export RAPIDS_VER=25.08.0        
export SPARK_VER=3.5.6
export SCALA_BIN=2.12             
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export NPROC=$(nproc)

# Derived variables
export CUDA_VER_DASH=${CUDA_VER/./-}

# Args: default to spark-only; use --all to include GPU drivers, CUDA and RAPIDS
INSTALL_ALL=false
for arg in "$@"; do
  case "$arg" in
    --all)
      INSTALL_ALL=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--all]"
      echo "  --all   Install NVIDIA driver, CUDA toolkit, and RAPIDS in addition to Spark"
      exit 0
      ;;
    *) ;;
  esac
done

# if [ "$INSTALL_ALL" = true ]; then
#   sudo apt-get update
#   sudo apt install -y build-essential dkms linux-headers-$(uname -r) \
#       software-properties-common pciutils
# fi

# # install openjdk-17-jdk
# sudo apt update
# sudo apt install -y build-essential git cmake ninja-build ccache pkg-config \
#   openjdk-17-jdk curl wget unzip zip

# # install maven
# curl -s "https://get.sdkman.io" | bash
# source "$HOME/.sdkman/bin/sdkman-init.sh"
# sdk install maven 3.9.6
# mvn -v

# if [ "$INSTALL_ALL" = true ]; then
#   # check ubuntu version
#   lsb_release -a | cat
# fi

# if [ "$INSTALL_ALL" = true ]; then
#   # install nvidia driver
#   sudo apt install -y nvidia-driver-570-server nvidia-utils-570-server

#   # install CUDA toolkit matching the OS version
#   UBUNTU_VERSION=$(lsb_release -rs || echo "")
#   if [[ "$UBUNTU_VERSION" == 22.04* ]]; then
#     CUDA_REPO_SUFFIX="ubuntu2204"
#   elif [[ "$UBUNTU_VERSION" == 20.04* ]]; then
#     CUDA_REPO_SUFFIX="ubuntu2004"
#   else
#     # default to 22.04 repo if detection fails
#     CUDA_REPO_SUFFIX="ubuntu2204"
#   fi

#   wget "https://developer.download.nvidia.com/compute/cuda/repos/${CUDA_REPO_SUFFIX}/x86_64/cuda-keyring_1.1-1_all.deb"
#   sudo dpkg -i cuda-keyring_1.1-1_all.deb
#   sudo apt-get update
#   sudo apt-get install -y "cuda-toolkit-${CUDA_VER_DASH}"

#   echo "export PATH=/usr/local/cuda-12.9/bin:\$PATH" | sudo tee /etc/profile.d/cuda.sh
#   echo "export LD_LIBRARY_PATH=/usr/local/cuda-12.9/lib64:\$LD_LIBRARY_PATH" | sudo tee -a /etc/profile.d/cuda.sh
#   source /etc/profile.d/cuda.sh

#   nvidia-smi | cat
#   nvcc --version
# fi

# install spark
cd $HOME && git clone https://github.com/apache/spark.git
cd spark && git checkout v${SPARK_VER}
git clean -xfd
rm -rf ~/.m2/repository/org/apache/spark

# ./dev/make-distribution.sh \
#   --name nocuda \
#   -Phadoop-3 -Pscala-${SCALA_BIN} \
#   -DskipTests -Dmaven.test.skip=true

# build distribution incl. Hive & ThriftServer (still skipping tests)
./dev/make-distribution.sh \
  --name withhive \
  -Phadoop-3 -Pscala-2.12 -Phive -Phive-thriftserver \
  -DskipTests -Dmaven.test.skip=true


ls -lh ./dist

export SPARK_HOME="$HOME/spark/dist"
[ -x "$SPARK_HOME/bin/spark-shell" ] && echo "OK: $SPARK_HOME" || { echo "BAD path" >&2; exit 1; }

echo 'export SPARK_HOME="$HOME/spark/dist"' >> ~/.bashrc
echo 'export PATH="$SPARK_HOME/bin:$PATH"'  >> ~/.bashrc
source ~/.bashrc
# check spark
"$SPARK_HOME/bin/spark-submit" --version
"$SPARK_HOME/bin/spark-shell"  --version
cat "$SPARK_HOME/RELEASE"

# check spark
"$SPARK_HOME/bin/run-example" SparkPi 1000
"$SPARK_HOME/bin/spark-shell" --master local[*] -i <(cat <<'SCALA'
val df = spark.range(0, 20000000).selectExpr("id","id % 10 AS g")
val agg = df.groupBy("g").count()
agg.explain("extended") // shows parsed, analyzed, optimized, and physical plan
println("Result: " + agg.collect().mkString(","))
System.exit(0)
SCALA
)


if [ "$INSTALL_ALL" = true ]; then
  # RAPIDS versions and Scala binary version already exported above
  export SPARK_HOME="$HOME/spark/dist"
  mkdir -p "$SPARK_HOME/jars/rapids"

  mvn -B -U dependency:get -Dartifact=com.nvidia:rapids-4-spark_2.12:25.08.0
  mvn -B -U dependency:get -Dartifact=com.nvidia:spark-rapids-jni:25.08.0
  mvn -B -U dependency:get -Dartifact=ai.rapids:cudf:25.08.0

  cp ~/.m2/repository/com/nvidia/rapids-4-spark_2.12/25.08.0/rapids-4-spark_2.12-25.08.0.jar \
     "$SPARK_HOME/jars/rapids/"
  cp ~/.m2/repository/com/nvidia/spark-rapids-jni/25.08.0/spark-rapids-jni-25.08.0.jar \
     "$SPARK_HOME/jars/rapids/"
  cp ~/.m2/repository/ai/rapids/cudf/25.08.0/cudf-25.08.0.jar \
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
fi

yes | sudo apt install python3-pip
pip install nvidia-ml-py3
