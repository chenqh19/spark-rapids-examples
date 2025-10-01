
sudo apt install python3.8-venv
python3 -m venv ~/venv/sparkrapids
source ~/venv/sparkrapids/bin/activate

pip install -U pip
pip install jupyterlab pyspark==3.5.6 pandas numpy matplotlib ipywidgets

export SPARK_HOME="$HOME/spark/dist"
mkdir -p "$SPARK_HOME/jars"
mv "$SPARK_HOME/jars/rapids/"*.jar "$SPARK_HOME/jars/" 2>/dev/null || true

ls -lh "$SPARK_HOME/jars" | egrep 'rapids|cudf'

export PYSPARK_DRIVER_PYTHON=jupyter
export PYSPARK_DRIVER_PYTHON_OPTS="lab --NotebookApp.default_url='/lab/tree/micro-benchmarks-cpu.ipynb'"

python -m ipykernel install --user --name sparkrapids --display-name "Python (sparkrapids)"



# export PYSPARK_SUBMIT_ARGS="\
#   --conf spark.plugins=com.nvidia.spark.SQLPlugin \
#   --conf spark.rapids.sql.enabled=true \
#   --conf spark.rapids.sql.allowMultipleJars=ALWAYS \
#   --conf spark.executor.resource.gpu.amount=1 \
#   --conf spark.task.resource.gpu.amount=0.125 \
#   --conf spark.rapids.sql.concurrentGpuTasks=2 \
#   --conf spark.executor.extraLibraryPath=/usr/local/cuda-12.9/lib64 \
#   --conf spark.driver.extraLibraryPath=/usr/local/cuda-12.9/lib64 \
#   pyspark-shell"
