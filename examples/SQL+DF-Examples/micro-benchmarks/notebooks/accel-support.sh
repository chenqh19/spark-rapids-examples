sudo chgrp sudo /dev/dsa/wq*
sudo chmod 660 /dev/dsa/wq*

sudo -E env HOME=/home/chenqh23 \
  SPARK_HOME=/home/chenqh23/spark/dist \
  QPL_INCLUDE=/home/chenqh23/qpl_install_dir/include \
  QPL_LIB=/home/chenqh23/qpl_install_dir/lib \
  LD_LIBRARY_PATH=/home/chenqh23/offload/iaa-compress/native/build:/home/chenqh23/qpl_install_dir/lib:$LD_LIBRARY_PATH \
  QPL_PATH=hardware \
  PATH=/home/chenqh23/venv/sparkrapids/bin:$PATH \
  /home/chenqh23/venv/sparkrapids/bin/python \
  /home/chenqh23/spark-rapids-examples/examples/SQL+DF-Examples/micro-benchmarks/notebooks/test_iaa.py