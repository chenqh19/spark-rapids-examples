set -euo pipefail
OUTDIR=/home/chenqh23/offload/dsa-agent/out
WRK=/home/chenqh23/offload/dsa-agent/outwork
BASE_JAR=/home/chenqh23/offload/dsa-agent/build/libs/dsa-agent-0.1.0.jar
SRC_TRANS=/home/chenqh23/offload/dsa-agent/src/main/java/com/example/dsa/agent/ArraycopyTransformer.java
SRC_DSA=/home/chenqh23/offload/dsa-agent/src/main/java/com/example/dsa/DsaArrayCopy.java
mkdir -p "$OUTDIR" "$WRK"
cd "$WRK"
rm -rf ./*
jar xf "$BASE_JAR"
JAVAC=${JAVA_HOME:-}/bin/javac
if [ ! -x "$JAVAC" ]; then JAVAC=javac; fi
"$JAVAC" -source 11 -target 11 -cp "$BASE_JAR" "$SRC_TRANS" "$SRC_DSA"
install -m 0644 /home/chenqh23/offload/dsa-agent/src/main/java/com/example/dsa/agent/ArraycopyTransformer*.class "$WRK/com/example/dsa/agent/"
install -m 0644 /home/chenqh23/offload/dsa-agent/src/main/java/com/example/dsa/DsaArrayCopy*.class "$WRK/com/example/dsa/"
jar cfm "$OUTDIR/dsa-agent-0.1.0.jar" META-INF/MANIFEST.MF .
jar tf "$OUTDIR/dsa-agent-0.1.0.jar" | grep -E 'com/example/dsa/(agent/ArraycopyTransformer|DsaArrayCopy)' || true


set -euo pipefail
OUTJAR=/home/chenqh23/offload/dsa-agent/out/dsa-agent-0.1.0.jar
WRK=/home/chenqh23/offload/dsa-agent/outwork
SRC_TRANS=/home/chenqh23/offload/dsa-agent/src/main/java/com/example/dsa/agent/ArraycopyTransformer.java
mkdir -p "$WRK"
cd "$WRK"
rm -rf ./*
jar xf "$OUTJAR"
JAVAC=${JAVA_HOME:-}/bin/javac
if [ ! -x "$JAVAC" ]; then JAVAC=javac; fi
"$JAVAC" -source 11 -target 11 -cp "$OUTJAR" "$SRC_TRANS"
install -m 0644 /home/chenqh23/offload/dsa-agent/src/main/java/com/example/dsa/agent/ArraycopyTransformer*.class \
  "$WRK/com/example/dsa/agent/"
jar cfm "$OUTJAR" META-INF/MANIFEST.MF .
jar tf "$OUTJAR" | grep 'com/example/dsa/agent/ArraycopyTransformer' || true


make -C /home/chenqh23/offload/dsa-agent/native clean hl \
  DML_INC=$HOME/dml_install_dir/include \
  DML_LIB=$HOME/dml_install_dir/lib \
  LDFLAGS="-shared -Wl,-rpath,$HOME/dml_install_dir/lib -Wl,--no-as-needed" \
  LDLIBS="-ldmlhl -ldml"