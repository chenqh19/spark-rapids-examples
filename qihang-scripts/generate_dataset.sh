#!/bin/bash

# Install sbt
echo "deb https://repo.scala-sbt.org/scalasbt/debian all main" | sudo tee /etc/apt/sources.list.d/sbt.list
echo "deb https://repo.scala-sbt.org/scalasbt/debian /" | sudo tee /etc/apt/sources.list.d/sbt_old.list
curl -sL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x2EE0EA64E40A89B84B2DF73499E82A75642AC823" | sudo apt-key add
sudo apt-get update
sudo apt-get install sbt

# Install jdk 
yes | sudo apt-get install openjdk-8-jdk

# clone related repos
cd $HOME/spark-rapids-examples
git clone https://github.com/databricks/spark-sql-perf.git
git clone https://github.com/databricks/tpcds-kit.git

cd tpcds-kit/tools
make OS=LINUX

# Build spark-sql-perf main jar
cd $HOME/spark-rapids-examples/spark-sql-perf
sbt clean package
JAR_MAIN=$(ls target/scala-*/spark-sql-perf_*-*.jar | grep -v tests | head -n1)

# Generate TPC-DS data with spark-shell + TPCDSTables
export SPARK_HOME="$HOME/spark/dist"
"$SPARK_HOME/bin/spark-shell" \
  --master local[*] --driver-memory 8g \
  --jars "$JAR_MAIN" \
  --conf spark.driver.extraJavaOptions="--add-opens=java.base/java.nio=ALL-UNNAMED --add-opens=java.base/sun.nio.ch=ALL-UNNAMED --add-opens=java.base/java.lang=ALL-UNNAMED" \
  --conf spark.executor.extraJavaOptions="--add-opens=java.base/java.nio=ALL-UNNAMED --add-opens=java.base/sun.nio.ch=ALL-UNNAMED --add-opens=java.base/java.lang=ALL-UNNAMED" \
  -i <(cat <<SCALA
import com.databricks.spark.sql.perf.tpcds.TPCDSTables
val toolsDir = "$HOME/spark-rapids-examples/tpcds-kit/tools"
val outRoot  = "$HOME/spark-rapids-examples/datasets/tpcds"
val scale    = "10"   // change as needed
val tables = new TPCDSTables(spark.sqlContext,
  dsdgenDir=toolsDir, scaleFactor=scale,
  useDoubleForDecimal=false, useStringForDate=false)
tables.genData(
  location=outRoot,
  format="parquet",
  overwrite=true,
  partitionTables=true,
  clusterByPartitionColumns=true,
  filterOutNullPartitionValues=false,
  tableFilter="",           // empty = all tables
  numPartitions=200         // tune for your machine
)
System.exit(0)
SCALA
)