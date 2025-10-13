# Build spark-sql-perf main jar
cd /users/chenqh23/spark-rapids-examples/spark-sql-perf
sbt clean package
JAR_MAIN=$(ls target/scala-*/spark-sql-perf_*-*.jar | grep -v tests | head -n1)

# Generate TPC-DS data with spark-shell + TPCDSTables
export SPARK_HOME="/users/chenqh23/spark/dist"
"$SPARK_HOME/bin/spark-shell" \
  --master local[*] --driver-memory 8g \
  --jars "$JAR_MAIN" \
  --conf spark.driver.extraJavaOptions="--add-opens=java.base/java.nio=ALL-UNNAMED --add-opens=java.base/sun.nio.ch=ALL-UNNAMED --add-opens=java.base/java.lang=ALL-UNNAMED" \
  --conf spark.executor.extraJavaOptions="--add-opens=java.base/java.nio=ALL-UNNAMED --add-opens=java.base/sun.nio.ch=ALL-UNNAMED --add-opens=java.base/java.lang=ALL-UNNAMED" \
  -i <(cat <<'SCALA'
import com.databricks.spark.sql.perf.tpcds.TPCDSTables
val toolsDir = "/users/chenqh23/spark-rapids-examples/tpcds-kit/tools"
val outRoot  = "/users/chenqh23/spark-rapids-examples/datasets/tpcds"
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