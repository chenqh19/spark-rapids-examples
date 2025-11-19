# Bootstrap defaults similar to GPU notebook
import os, glob, psutil

# Ensure SPARK_HOME is set (fallback to local build dist)
SPARK_HOME = os.environ.get("SPARK_HOME", "/home/chenqh23/spark/dist")
os.environ["SPARK_HOME"] = SPARK_HOME
os.environ['JAVA_HOME'] = os.environ.get('JAVA_HOME', '/usr/lib/jvm/java-17-openjdk-amd64')

# Clean up lingering SparkSubmit JVMs that can cause empty Py4J answers
for p in psutil.process_iter(['pid','name','cmdline']):
    cl = ' '.join(p.info.get('cmdline') or [])
    if p.info.get('name') == 'java' and 'org.apache.spark.deploy.SparkSubmit' in cl:
        try:
            p.kill()
        except Exception:
            pass

# Ensure findspark can locate Spark
try:
    import findspark; findspark.init(os.environ['SPARK_HOME'])
except Exception:
    pass

# Use local mode unless a cluster URL is provided
os.environ.setdefault("SPARK_MASTER_URL", "local[*]")

# Data and event log defaults
os.environ.setdefault("DATA_ROOT", "/home/chenqh23/spark-rapids-examples/datasets")
os.environ.setdefault("EVENTLOG_DIR", "/tmp/spark-events")
try:
    os.makedirs(os.environ["EVENTLOG_DIR"], exist_ok=True)
except Exception:
    pass

print("SPARK_HOME =", os.environ["SPARK_HOME"]) 
print("SPARK_MASTER_URL =", os.environ["SPARK_MASTER_URL"]) 
print("EVENTLOG_DIR =", os.environ["EVENTLOG_DIR"]) 

def runMicroBenchmark(spark, appName, query, retryTimes):
    count = 0
    total_time = 0
    # You can print the physical plan of each query
    # spark.sql(query).explain()
    while count < retryTimes:
        start = time.time()
        spark.sql(query).collect()
        end = time.time()
        total_time += round(end - start, 2)
        count = count + 1
        print("Retry times : {}, ".format(count) + appName + " microbenchmark takes {} seconds".format(round(end - start, 2)))
    print(appName + " microbenchmark takes average {} seconds after {} retries".format(round(total_time/retryTimes),retryTimes))
    with open('result.txt', 'a') as file:
        file.write("{},{},{}\n".format(appName, round(total_time/retryTimes), retryTimes))

# You need to update data path with your real path and hardware resource!
from pyspark.sql import SparkSession
from pyspark.conf import SparkConf
import time, os

# Java 17 add-opens flags (harmless on Java 8+)
_DEF_OPENS = (
    "--add-opens=java.base/java.lang=ALL-UNNAMED "
    "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED "
    "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED "
    "--add-opens=java.base/java.io=ALL-UNNAMED "
    "--add-opens=java.base/java.net=ALL-UNNAMED "
    "--add-opens=java.base/java.nio=ALL-UNNAMED "
    "--add-opens=java.base/java.util=ALL-UNNAMED "
    "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED "
    "--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED "
    "--add-opens=java.base/jdk.internal.ref=ALL-UNNAMED "
    "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED "
    "--add-opens=java.base/sun.nio.cs=ALL-UNNAMED "
    "--add-opens=java.base/sun.security.action=ALL-UNNAMED "
    "--add-opens=java.base/sun.util.calendar=ALL-UNNAMED"
)

# Build base conf (GPU-style settings but CPU-only)
base = (SparkConf()
    .setMaster(os.environ.get("SPARK_MASTER_URL", "local[*]"))
    .setAppName("Microbenchmark on CPU")
    .set("spark.driver.memory", os.environ.get("DRIVER_MEM", "12g"))
    .set("spark.sql.adaptive.enabled", "true")
    .set("spark.sql.files.maxPartitionBytes", os.environ.get("MAX_PARTITION_BYTES", "128m"))
    .set("spark.sql.shuffle.partitions", os.environ.get("SHUFFLE_PARTITIONS", "96"))
    .set("spark.locality.wait", "0")
    .set("spark.scheduler.mode", "FAIR")
    .set("spark.eventLog.enabled", "false")
    .set("spark.driver.extraJavaOptions", _DEF_OPENS)
    .set("spark.executor.extraJavaOptions", _DEF_OPENS)
    # IAA compression codec wiring
    .set("spark.jars", "/home/chenqh23/offload/iaa-compress/iaa-codec.jar")
    .set("spark.io.compression.codec", "org.apache.spark.io.IaaCompressionCodec")
    .set("spark.io.compression.iaa.blockSize", os.environ.get("IAA_BLOCK_SIZE", "262144"))
    .set("spark.driver.extraLibraryPath", "/home/chenqh23/offload/iaa-compress/native/build:/home/chenqh23/qpl_install_dir/lib")
    .set("spark.executor.extraLibraryPath", "/home/chenqh23/offload/iaa-compress/native/build:/home/chenqh23/qpl_install_dir/lib")
)

# create spark session
spark = SparkSession.builder.config(conf=base).getOrCreate()

# IAA sanity check: confirm hardware path availability via QPL HW job init
jvm = spark._jvm
iaa = jvm.org.apache.spark.io.IAA
try:
    hw_ok = bool(iaa.isHardwareAvailable())
except Exception as e:
    hw_ok = False
    print("IAA isHardwareAvailable() check failed:", e)
print("IAA hardware available:", hw_ok)

# Note: codec in use
print("spark.io.compression.codec =", spark.conf.get("spark.io.compression.codec"))

dataRoot = os.environ.get("DATA_ROOT", "/home/chenqh23/spark-rapids-examples/datasets")

# Load dataframe and create tempView (avoid extreme repartition)
spark.read.parquet(dataRoot + "/tpcds/customer").createOrReplaceTempView("customer")
spark.read.parquet(dataRoot + "/tpcds/store_sales").createOrReplaceTempView("store_sales")
spark.read.parquet(dataRoot + "/tpcds/catalog_sales").createOrReplaceTempView("catalog_sales")
spark.read.parquet(dataRoot + "/tpcds/web_sales").createOrReplaceTempView("web_sales")
spark.read.parquet(dataRoot + "/tpcds/item").createOrReplaceTempView("item")
spark.read.parquet(dataRoot + "/tpcds/date_dim").createOrReplaceTempView("date_dim")

# Cache hot tables to reduce I/O contention during parallel runs
for t in ("customer","store_sales","catalog_sales","web_sales","item","date_dim"):
    try:
        spark.catalog.cacheTable(t)
    except Exception:
        pass
# Materialize caches once to warm up
for t in ("customer","store_sales","catalog_sales","web_sales","item","date_dim"):
    _ = spark.table(t).count()

print("-"*50)
time.sleep(2)

query3 = '''
select i_item_sk ss_item_sk
 from item,
    (select iss.i_brand_id brand_id, iss.i_class_id class_id, iss.i_category_id category_id
     from store_sales, item iss, date_dim d1
     where ss_item_sk = iss.i_item_sk
                    and ss_sold_date_sk = d1.d_date_sk
       and d1.d_year between 1999 AND 1999 + 2
   intersect
     select ics.i_brand_id, ics.i_class_id, ics.i_category_id
     from catalog_sales, item ics, date_dim d2
     where cs_item_sk = ics.i_item_sk
       and cs_sold_date_sk = d2.d_date_sk
       and d2.d_year between 1999 AND 1999 + 2
   intersect
     select iws.i_brand_id, iws.i_class_id, iws.i_category_id
     from web_sales, item iws, date_dim d3
     where ws_item_sk = iws.i_item_sk
       and ws_sold_date_sk = d3.d_date_sk
       and d3.d_year between 1999 AND 1999 + 2) x
 where i_brand_id = brand_id
   and i_class_id = class_id
   and i_category_id = category_id
'''

# Run microbenchmark with n retry time
runMicroBenchmark(spark,"NDS Q14a subquery", query3, 2)
time.sleep(2)