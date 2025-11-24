sudo chgrp sudo /dev/dsa/wq*
sudo chmod 660 /dev/dsa/wq*

sudo -E env HOME=$HOME \
  SPARK_HOME=$HOME/spark/dist \
  QPL_INCLUDE=$HOME/qpl_install_dir/include \
  QPL_LIB=$HOME/qpl_install_dir/lib \
  LD_LIBRARY_PATH=$HOME/offload/iaa-compress/native/build:$HOME/qpl_install_dir/lib:$LD_LIBRARY_PATH \
  QPL_PATH=hardware \
  PATH=$HOME/venv/sparkrapids/bin:$PATH \
  $HOME/venv/sparkrapids/bin/python \
  $HOME/spark-rapids-examples/examples/SQL+DF-Examples/micro-benchmarks/notebooks/test_iaa.py