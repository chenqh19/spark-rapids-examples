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

# Export Intel DML paths for this notebook (driver process)
HOME = os.path.expanduser("~")
os.environ.setdefault("DML_INC", f"{HOME}/dml_install_dir/include")
os.environ.setdefault("DML_LIB", f"{HOME}/dml_install_dir/lib")

print("SPARK_HOME =", os.environ["SPARK_HOME"]) 
print("SPARK_MASTER_URL =", os.environ["SPARK_MASTER_URL"]) 
print("EVENTLOG_DIR =", os.environ["EVENTLOG_DIR"]) 
print("DML_INC =", os.environ["DML_INC"]) 
print("DML_LIB =", os.environ["DML_LIB"]) 

from pyspark.sql import SparkSession
from pyspark.conf import SparkConf
import os, time

dataRoot = os.environ.get("DATA_ROOT", "/users/chenqh23/spark-rapids-examples/datasets")

def _pick_jar() -> str:
    candidates = [
        "/home/chenqh23/offload/dsa-agent/out/dsa-agent-0.1.0.jar",
        "/home/chenqh23/offload/dsa-agent/build/libs/dsa-agent-0.1.0.jar",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]

_DSA_AGENT_JAR = _pick_jar()
_DSA_NATIVE_DIR = "/home/chenqh23/offload/dsa-agent/native"

# Ensure native libs are discoverable by environment too
os.environ["LD_LIBRARY_PATH"] = f"{_DSA_NATIVE_DIR}:{os.environ.get('DML_LIB','')}:{os.environ.get('QPL_LIB','')}:{os.environ.get('LD_LIBRARY_PATH','')}"

_DEF_OPENS = (
    "--add-opens=java.base/java.lang=ALL-UNNAMED "
    "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED "
    "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED "
    "--add-opens=java.base/java.io=ALL-UNNAMED "
    "--add-opens=java.base/java.net=ALL-UNNAMED "
    "--add-opens=java.base/java.nio=ALL-UNNAMED "
    "--add-opens=java.base/java.util=ALL-UNNAMED "
    "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED "
    "--add-opens=java.base/jdk.internal.ref=ALL-UNNAMED "
    "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED "
)

base = (SparkConf()
    .setMaster(os.environ.get("SPARK_MASTER_URL", "local[*]"))
    .setAppName("Microbenchmark (Accel)")
    .set("spark.driver.memory", os.environ.get("DRIVER_MEM", "12g"))
    .set("spark.sql.adaptive.enabled", "true")
    .set("spark.sql.files.maxPartitionBytes", os.environ.get("MAX_PARTITION_BYTES", "128m"))
    .set("spark.sql.shuffle.partitions", os.environ.get("SHUFFLE_PARTITIONS", "32"))
    .set("spark.locality.wait", "0")
    .set("spark.scheduler.mode", "FAIR")
    .set("spark.eventLog.enabled", "false")
)

jar_exists = os.path.exists(_DSA_AGENT_JAR)
native_exists = os.path.exists(os.path.join(_DSA_NATIVE_DIR, "libdsa_copy.so"))
if jar_exists:
    # Always add agent classes; native loading is controlled below
    base = (base
        .set("spark.driver.extraClassPath", _DSA_AGENT_JAR)
        .set("spark.driver.extraJavaOptions",
             f"{_DEF_OPENS} -Xbootclasspath/a:{_DSA_AGENT_JAR} "
             f"-javaagent:{_DSA_AGENT_JAR} -Djava.library.path={_DSA_NATIVE_DIR} -Ddsa.skip.retransform=true")
        .set("spark.driver.extraLibraryPath",
             f"{_DSA_NATIVE_DIR}:{os.environ.get('DML_LIB','')}:{os.environ.get('QPL_LIB','')}")
    )
else:
    print("DSA agent jar not found:", _DSA_AGENT_JAR)
if not native_exists:
    print("Warning: native lib missing at", os.path.join(_DSA_NATIVE_DIR, "libdsa_copy.so"))

# Optional: one-shot test to rule out agent-caused crash
# base = base.set("spark.driver.extraJavaOptions", f"{_DEF_OPENS} -Ddsa.disable=true") \
#            .set("spark.executor.extraJavaOptions", f"{_DEF_OPENS} -Ddsa.disable=true")

spark = SparkSession.builder.config(conf=base).getOrCreate()

# DSA sanity check (bootstrap-load the JNI, then verify)
jvm = spark._jvm
print("java.library.path:", jvm.java.lang.System.getProperty("java.library.path"))
print("LD_LIBRARY_PATH:", jvm.java.lang.System.getenv("LD_LIBRARY_PATH"))

Array = jvm.java.lang.reflect.Array
ByteTYPE = jvm.java.lang.Byte.TYPE

n = 10_000_000
src = Array.newInstance(ByteTYPE, n)
dst = []
for i in range(10):
    dst.append(Array.newInstance(ByteTYPE, n))


Dsa = jvm.com.example.dsa.DsaArrayCopy
# Ensure the bootstrap classloader loads the JNI from the standard path
native_lib_path = "/home/chenqh23/offload/dsa-agent/native/libdsa_copy.so"
jvm.java.lang.System.setProperty("dsa.native.path", native_lib_path)
print("using dsa.native.path:", native_lib_path)
print("ensureNativeLoaded:", Dsa.ensureNativeLoaded())

try:
    print("isDmlBuilt:", Dsa.isDmlBuilt())
except Exception as e:
    print("isDmlBuilt call failed:", e)

print("backend_before:", Dsa.getLastBackend())
for i in range(10):
    Dsa.arraycopy(src, 0, dst[i], 0, n)
    print("backend_after:", Dsa.getLastBackend(), "dmlStatus:", Dsa.getLastDmlStatus())
print("Note: backend=2=DML, 1=memmove-after-DML-fail, 0=memmove")