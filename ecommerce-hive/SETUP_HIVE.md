# Setting up Hive in WSL Ubuntu (simplest working demo)

This installs Hive in your existing **Ubuntu** WSL distribution and runs it on
local files. There are no HDFS services to start: only one program,
HiveServer2, has to be running. The Windows venv then talks to it through
PyHive at `localhost:10000`, which is what `python/config.py` already expects.

Run every command below inside Ubuntu (Start menu → Ubuntu), one block at a time.

## 1. Install Java 8

Hive 3 needs Java 8. The JDK 25 on Windows is not used.

```bash
sudo apt update && sudo apt install -y openjdk-8-jdk-headless
```

## 2. Download Hadoop and Hive (about 1 GB)

Hive needs Hadoop's libraries even though no Hadoop service will run.

```bash
cd ~
wget https://archive.apache.org/dist/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz
wget https://archive.apache.org/dist/hive/hive-3.1.3/apache-hive-3.1.3-bin.tar.gz
tar -xzf hadoop-3.3.6.tar.gz
tar -xzf apache-hive-3.1.3-bin.tar.gz
```

## 3. Set environment variables

```bash
cat >> ~/.bashrc <<'EOF'
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export HADOOP_HOME=$HOME/hadoop-3.3.6
export HIVE_HOME=$HOME/apache-hive-3.1.3-bin
export PATH=$PATH:$HADOOP_HOME/bin:$HIVE_HOME/bin
EOF
source ~/.bashrc
```

Check: `hadoop version` should print `Hadoop 3.3.6`.

## 4. Fix the Guava library clash

Hive 3.1.3 ships an older Guava than Hadoop 3.3.6 and will not start without this.

```bash
rm $HIVE_HOME/lib/guava-19.0.jar
cp $HADOOP_HOME/share/hadoop/hdfs/lib/guava-27.0-jre.jar $HIVE_HOME/lib/
```

## 5. Configure Hive

```bash
cat > $HIVE_HOME/conf/hive-site.xml <<'EOF'
<?xml version="1.0"?>
<configuration>
  <property>
    <name>javax.jdo.option.ConnectionURL</name>
    <value>jdbc:derby:;databaseName=/home/niranjan/metastore_db;create=true</value>
  </property>
  <property>
    <name>hive.metastore.warehouse.dir</name>
    <value>/user/hive/warehouse</value>
  </property>
  <property>
    <name>hive.server2.enable.doAs</name>
    <value>false</value>
  </property>
</configuration>
EOF
```

Give Hive a 1 GB Java heap. With the default 256 MB, `03_load_data.sql` fails
with `OutOfMemoryError: Java heap space`.

```bash
echo 'export HADOOP_HEAPSIZE=1024' >> $HIVE_HOME/conf/hive-env.sh
```

## 6. Create the warehouse folder and copy the CSVs

The staging tables in `hive/02_create_tables.sql` read from these exact folders.

```bash
sudo mkdir -p /user/hive/warehouse
sudo chown -R $USER /user

DATA="/mnt/c/Users/Niranjan/Documents/BDA Project/ecommerce-hive/data"
for t in customers products orders order_items payments; do
  mkdir -p /user/hive/warehouse/ecommerce/staging/$t
  cp "$DATA/$t.csv" /user/hive/warehouse/ecommerce/staging/$t/
done
```

## 7. Initialise the metastore (first time only)

```bash
schematool -dbType derby -initSchema
```

It should end with `schemaTool completed`.

## 8. Start HiveServer2

```bash
hiveserver2
```

Leave this window open. It takes about a minute to be ready and prints little.
This is the only thing you need to start each time you want to use Hive.

## 9. Create and load the tables

Open a **second** Ubuntu window:

```bash
SQL="/mnt/c/Users/Niranjan/Documents/BDA Project/ecommerce-hive/hive"
for f in 01_create_database 02_create_tables 03_load_data 04_transform_data; do
  beeline -u jdbc:hive2://localhost:10000 -n hive -f "$SQL/$f.sql" || break
done
```

If the first one says "Connection refused", HiveServer2 is still starting;
wait and run it again. `03_load_data.sql` takes a few minutes and finishes
with a row count for each of the five tables.

## 10. Query from the venv with PyHive

Back in Windows PowerShell, from `ecommerce-hive`:

```powershell
..\.venv\Scripts\python.exe benchmark\benchmark.py
```

Then open the dashboard at http://localhost:8501 and choose **Hive Mode** in
the sidebar. Each chart takes several seconds because Hive runs a job per query.

## Notes

- These steps were run on this PC on 4 Oct 2026 and the dashboard worked in Hive Mode.
- Ubuntu has about 3 GB of memory, so close other heavy programs during step 9.
- To start over: stop HiveServer2 with Ctrl+C, then
  `rm -rf ~/metastore_db /user/hive/warehouse/ecommerce.db` and repeat from step 7.
