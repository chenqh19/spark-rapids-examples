# %% [markdown]
# # Microbenchmarks on CPU
# This is a notebook for microbenchmarks running on CPU.

# %%
# Bootstrap defaults similar to GPU notebook
import os, glob, psutil

# Ensure SPARK_HOME is set (fallback to local build dist)
SPARK_HOME = os.environ.get("SPARK_HOME", os.environ["HOME"] + "/spark/dist")
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
os.environ.setdefault("DATA_ROOT", os.environ["HOME"] + "/spark-rapids-examples/datasets")
os.environ.setdefault("EVENTLOG_DIR", "/tmp/spark-events")
try:
    os.makedirs(os.environ["EVENTLOG_DIR"], exist_ok=True)
except Exception:
    pass

print("SPARK_HOME =", os.environ["SPARK_HOME"]) 
print("SPARK_MASTER_URL =", os.environ["SPARK_MASTER_URL"]) 
print("EVENTLOG_DIR =", os.environ["EVENTLOG_DIR"]) 

# %% [markdown]
# Run the microbenchmark with retry times

# %%
def runMicroBenchmark(spark, appName, query, retryTimes):
    count = -2
    total_time = 0.0
    # You can print the physical plan of each query
    # spark.sql(query).explain()
    while count < retryTimes:
        start = time.time()
        spark.sql(query).collect()
        end = time.time()
        if count >= 0:
            total_time += (end - start)
        count = count + 1
        print("Retry times : {}, ".format(count) + appName + " microbenchmark takes {:.2f} seconds".format(end - start))
    avg = total_time / float(retryTimes) if retryTimes > 0 else 0.0
    print(appName + " microbenchmark takes average {:.2f} seconds after {} retries".format(avg, retryTimes))
    with open('result.txt', 'a') as file:
        file.write("{},{:.2f},{}\n".format(appName, avg, retryTimes))

# %%
# IAA filter counters helper (uses iaa-filter JNI if present)

def _iaa_jni():
    try:
        return spark._jvm.com.intel.spark.iaa.jni.IaaJni
    except Exception:
        return None


def run_with_iaa(spark, appName, query, retryTimes):
    import time
    jni = _iaa_jni()
    if jni is not None:
        try:
            jni.setFilterCountersEnabled(True)
        except Exception:
            pass
        try:
            hw0 = int(jni.getHwFilterJobs())
            sw0 = int(jni.getSwFilterJobs())
        except Exception:
            hw0 = sw0 = 0
    else:
        hw0 = sw0 = 0

    runMicroBenchmark(spark,"NDS Q14a subquery", query3, 10)

    if jni is not None:
        try:
            hw1 = int(jni.getHwFilterJobs())
            sw1 = int(jni.getSwFilterJobs())
        except Exception:
            hw1 = hw0
            sw1 = sw0
    else:
        hw1 = hw0
        sw1 = sw0

    print(f"IAA_HW_FILTER_JOBS_DELTA={hw1 - hw0}, IAA_SW_FILTER_JOBS_DELTA={sw1 - sw0}")



# %%
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

# Build base conf (use IAA filter plugin)
base = (SparkConf()
    .setMaster(os.environ.get("SPARK_MASTER_URL", "local[*]"))
    .setAppName("Microbenchmark on CPU")
    .set("spark.driver.memory", os.environ.get("DRIVER_MEM", "12g"))
    .set("spark.sql.adaptive.enabled", "true")
    .set("spark.sql.files.maxPartitionBytes", os.environ.get("MAX_PARTITION_BYTES", "128m"))
    .set("spark.sql.shuffle.partitions", os.environ.get("SHUFFLE_PARTITIONS", "32"))
    .set("spark.locality.wait", "0")
    .set("spark.scheduler.mode", "FAIR")
    .set("spark.eventLog.enabled", "false")
    .set("spark.driver.extraJavaOptions", _DEF_OPENS)
    .set("spark.executor.extraJavaOptions", _DEF_OPENS)
    # IAA filter plugin wiring
    .set("spark.sql.extensions", "com.intel.spark.iaa.IaaSparkExtensions")
    .set("spark.jars", os.environ["HOME"] + "/offload/iaa-filter/target/iaa-filter-0.1.0.jar")
    .set("spark.driver.extraLibraryPath", os.environ["HOME"] + "/offload/iaa-filter/native/build/target:" + os.environ["HOME"] + "/qpl_install_dir/lib")
    .set("spark.executor.extraLibraryPath", os.environ["HOME"] + "/offload/iaa-filter/native/build/target:" + os.environ["HOME"] + "/qpl_install_dir/lib")
)

# create spark session
spark = SparkSession.builder.config(conf=base).getOrCreate()


# %%
# IAA sanity check: confirm hardware path availability via QPL HW job init
jvm = spark._jvm
iaa = jvm.org.apache.spark.io.IAA
try:
    hw_ok = bool(iaa.isHardwareAvailable())
except Exception as e:
    hw_ok = False
    print("IAA isHardwareAvailable() check failed:", e)
print("IAA hardware available:", hw_ok)



# %%
# Metrics gate: disable counts/histogram when spark.io.compression.iaa.stats=false
from typing import Tuple, List

_STATS_ON = str(spark.conf.get("spark.io.compression.iaa.stats", "false")).lower() == "true"

# Override helpers to honor the gate

def get_iaa_counts() -> Tuple[int, int, int]:
    if not _STATS_ON:
        return (0, 0, 0)
    m = spark._jvm.org.apache.spark.io.IAA
    try:
        hw = int(m.getHwCompressJobs())
        sw = int(m.getSwCompressJobs())
        pt = int(m.getPassthroughCompressJobs())
    except Exception:
        hw = sw = pt = 0
    return (hw, sw, pt)


def print_iaa_counts_delta(title: str, before, after):
    if not _STATS_ON:
        return
    dhw = after[0] - before[0]
    dsw = after[1] - before[1]
    dpt = after[2] - before[2]
    print(f"IAA path counts for {title} (this run only):")
    print(f"HW: {dhw}, SW: {dsw}, Passthrough: {dpt}")


def get_comp_hist() -> Tuple[List[int], List[int], List[str]]:
    if not _STATS_ON:
        return [], [], []
    m = spark._jvm.org.apache.spark.io.IAA
    try:
        lowers = list(m.getCompressedBucketLowers())
        counts = list(m.getCompressedBucketCounts())
        labels = list(m.getCompressedBucketLabels())
    except Exception:
        lowers, counts, labels = [], [], []
    return lowers, counts, labels


def print_comp_hist_delta(title: str, before, after):
    if not _STATS_ON:
        return
    b_lowers, b_counts, _ = before
    a_lowers, a_counts, a_labels = after
    if not a_lowers:
        return
    b_map = {lb: bc for lb, bc in zip(b_lowers, b_counts)}
    print(f"Compressed-size histogram for {title} (this run only):")
    for lb, cnt, lbl in zip(a_lowers, a_counts, a_labels):
        prev = b_map.get(lb, 0)
        delta = cnt - prev
        if delta:
            print(f"{lbl}: {delta}")



# %%
dataRoot = os.environ.get("DATA_ROOT", os.environ["HOME"] + "/spark-rapids-examples/datasets")

# Load dataframe and create tempView (avoid extreme repartition)
spark.read.parquet(dataRoot + "/tpcds/customer").createOrReplaceTempView("customer")
spark.read.parquet(dataRoot + "/tpcds/store_sales").createOrReplaceTempView("store_sales")
spark.read.parquet(dataRoot + "/tpcds/catalog_sales").createOrReplaceTempView("catalog_sales")
spark.read.parquet(dataRoot + "/tpcds/web_sales").createOrReplaceTempView("web_sales")
spark.read.parquet(dataRoot + "/tpcds/item").createOrReplaceTempView("item")
spark.read.parquet(dataRoot + "/tpcds/date_dim").createOrReplaceTempView("date_dim")

# # Cache hot tables to reduce I/O contention during parallel runs
# for t in ("customer","store_sales","catalog_sales","web_sales","item","date_dim"):
#     try:
#         spark.catalog.cacheTable(t)
#     except Exception:
#         pass
# # Materialize caches once to warm up
# for t in ("customer","store_sales","catalog_sales","web_sales","item","date_dim"):
#     _ = spark.table(t).count()

print("-"*50)
time.sleep(2)

# %% [markdown]
# ### Windowing (without data skew)
# This is a microbenchmark about windowing expressions running on CPU mode. The sub-query calculates the average ss_sales_price of a fixed window function partition by ss_customer_sk, and the parent query calculates the average price of the sub-query grouping by each customer.

# %%
query1 = '''
select ss_customer_sk,avg(avg_price) as avg_price
from
(
SELECT ss_customer_sk ,avg(ss_sales_price) OVER (PARTITION BY ss_customer_sk order by ss_sold_date_sk ROWS BETWEEN 50 PRECEDING AND 50 FOLLOWING ) as avg_price
FROM store_sales
where ss_customer_sk is not null
) group by ss_customer_sk order by 2 desc 
'''
print("-"*50)

# %%
# Run microbenchmark with n retry time
before_counts = get_iaa_counts()
before_hist = get_comp_hist()
runMicroBenchmark(spark,"Windowing without skew", query1, 10)
after_counts = get_iaa_counts()
after_hist = get_comp_hist()
print_iaa_counts_delta("Windowing without skew", before_counts, after_counts)
print_comp_hist_delta("Windowing without skew", before_hist, after_hist)

time.sleep(2)

# %% [markdown]
# ### Intersection
# This is a microbenchmark about intersection operation running on CPU mode. The query calculates items in the same brand, class, and category that are sold in all three sales channels in two consecutive years.

# %%
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

# %%
# Run microbenchmark with n retry time
before_counts = get_iaa_counts()
before_hist = get_comp_hist()
# runMicroBenchmark(spark, "NDS Q14a subquery", query3, 10)
run_with_iaa(spark, "NDS Q14a subquery", query3, 10)

after_counts = get_iaa_counts()
after_hist = get_comp_hist()
print_iaa_counts_delta("NDS Q14a subquery", before_counts, after_counts)
print_comp_hist_delta("NDS Q14a subquery", before_hist, after_hist)

time.sleep(2)

# %%
# Simple IAA filter query (int range on date_dim)
query_iaa_simple = '''
select d_year
from date_dim
where d_year >= 1999
'''

# %%
# Confirm IAA filter usage on the simple query (run after Spark session is created)
try:
    run_with_iaa(spark, "IAA simple year filter", query_iaa_simple, 1)
except NameError:
    print("Run this cell after creating the Spark session and helper functions.")



# %%
# Run after Spark session is created
spark.conf.set("spark.sql.debug.maxToStringFields", 1000)

def show_plan(title, query):
    df = spark.sql(query)
    print(f"=== {title} - explain(True) ===")
    df.explain(True)
    print(f"=== {title} - executedPlan.treeString ===")
    try:
        print(df._jdf.queryExecution().executedPlan().treeString())
    except Exception as e:
        print("executedPlan.treeString unavailable:", e)

    try:
        plan_str = df._jdf.queryExecution().executedPlan().toString()
        print("Uses IaaFilter:", "IaaFilter" in plan_str)
    except Exception:
        pass

show_plan("IAA simple year filter", query_iaa_simple)
# show_plan("NDS Q14a subquery", query3)

# %%
import uuid, os, time
tmp = os.path.join("/tmp", "iaa_tmp_" + str(uuid.uuid4()))

# 1) Fewer writers -> one Parquet file
spark.range(0, 1_000_000) \
     .repartition(1) \
     .selectExpr("CAST(id % 64 AS INT) AS id") \
     .write.mode("overwrite").parquet(tmp)

# 2) Larger columnar batches and lower parallelism
spark.conf.set("spark.sql.parquet.columnarReaderBatchSize", "16384")
spark.conf.set("spark.default.parallelism", "4")
spark.conf.set("spark.sql.shuffle.partitions", "4")

# 3) Read with a single partition to keep HW queue pressure low
df = spark.read.parquet(tmp).repartition(1)
df.createOrReplaceTempView("iaa_tmp")

sql_simple = "SELECT id FROM iaa_tmp WHERE id < 5"
df = spark.sql(sql_simple)
df.explain(True)

jni = None
try:
    jni = spark._jvm.com.intel.spark.iaa.jni.IaaJni
    jni.setFilterCountersEnabled(True)
    hw0, sw0 = int(jni.getHwFilterJobs()), int(jni.getSwFilterJobs())
except Exception:
    hw0 = sw0 = 0

t0 = time.time(); df.count(); t1 = time.time()
if jni is not None:
    hw1, sw1 = int(jni.getHwFilterJobs()), int(jni.getSwFilterJobs())
    print("IAA_HW_FILTER_JOBS_DELTA=", hw1 - hw0, "IAA_SW_FILTER_JOBS_DELTA=", sw1 - sw0)
print(f"elapsed_ms={(t1 - t0)*1000:.2f}")


