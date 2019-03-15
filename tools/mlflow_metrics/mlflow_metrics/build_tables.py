from __future__ import print_function
from pyspark.sql import SparkSession, Row

import traceback
import os, time
import mlflow
from mlflow_metrics import mlflow_utils, file_api
mlflow_utils.dump_mlflow_info()

mlflow_client = mlflow.tracking.MlflowClient()
spark = SparkSession.builder.appName("mlflow_metrics").enableHiveSupport().getOrCreate()

class BuildTables(object):
    def __init__(self, database, data_dir, use_parquet=False):
        print("database:",database)
        print("data_dir:",data_dir)
        print("use_parquet:",use_parquet)
        self.database = database
        self.data_dir = data_dir
        self.use_parquet = use_parquet
        self.file_api = file_api.get_file_api(data_dir)
        print("file_api:",type(self.file_api).__name__)
        self.delimiter = "\t"
        self.logmod = 20

    def _create_database(self):
        spark.sql("drop database if exists {} cascade".format(self.database))
        spark.sql("create database {}".format(self.database))

    def _strip_underscores(self, obj):
        return { k[1:]:v for (k,v) in obj.__dict__.items() }

    def _mk_data_path(self,table):
        return self.data_dir + "/" + table

    def _mk_dir(self, table):
        path = self._mk_data_path(table)
        if not os.path.exists(path):
            os.makedirs(path)

    def _write_df(self, df, table):
        df = df.coalesce(1)
        if self.use_parquet:
            df.write.mode("overwrite").parquet(self._mk_data_path(table))
        else:
            df.write.option("header","true").option("sep",self.delimiter).mode("overwrite").csv(self._mk_data_path(table))

    def _build_experiment(self, experiment_id, idx=None,num_exps=None):
        try:
            infos = mlflow_client.list_run_infos(experiment_id)
            if idx is None:
                print("Experiment {} has {} runs".format(experiment_id,len(infos)))
            else:
                print("{}/{}: Experiment {} has {} runs".format((1+idx),num_exps,experiment_id,len(infos)))
            rows = []
            if len(infos) == 0:
                print("WARNING: No runs for experiment {}".format(exp))
                return 0
            for j,info in enumerate(infos):
                if j%self.logmod==0: print("  run {}/{} of experiment {}".format(j,len(infos),experiment_id))
                run = mlflow_client.get_run(info.run_uuid)
                dct = self._strip_underscores(info)
                params = { "_p_"+x.key:x.value for x in run.data.params }
                metrics = { "_m_"+x.key:x.value for x in run.data.metrics }
                dct.update(params)
                dct.update(metrics)
                rows.append(dct)
            df = spark.createDataFrame(rows)
            table = "exp_"+str(experiment_id)
            self._write_df(df,table)
            self._build_table_ddl(table)
            return len(infos)
        except Exception as e:
            print("WARNING: Cannot list runs for experiment {} {}".format(experiment_id,e))
            traceback.print_exc()
            return 0

    def _build_status_table(self):
        rtime = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))
        print("Refreshed at:",rtime)
        tracking_uri = mlflow.tracking.get_tracking_uri()
        rows = [ Row(refreshed_at=rtime, \
            tracking_uri = tracking_uri,\
            tracking_host = mlflow_utils.get_host(tracking_uri), \
            version = mlflow.version.VERSION) ]
        df = spark.createDataFrame(rows)
        self._write_df(df,"mlflow_status")

    def _build_table_ddl(self, table):
        path = self._mk_data_path(table)
        table = self.database + "." + table
        spark.sql("drop table if exists {}".format(table))
        if self.use_parquet:
            spark.sql('CREATE TABLE {} USING PARQUET\
                OPTIONS (path = "{}") \
                '.format(table,path))
        else:
            spark.sql('CREATE TABLE {} USING CSV\
                OPTIONS (path = "{}", header "true", inferSchema "true", delimiter "{}") \
                '.format(table,path,self.delimiter))

    def _build_all_ddl(self):
        spark.sql("create database if not exists "+self.database)
        self._build_table_ddl("mlflow_status")

    def _build_all_data(self, exp_ids):
        self._mk_dir("mlflow_status")
        self._build_status_table()
        exps = mlflow_client.list_experiments() 
        if len(exp_ids) > 0:
            exps = [ exp for exp in exps if exp.experiment_id in set(exp_ids) ]
        print("Found {} experiments".format(len(exps)))
        if len(exps) == 0:
            print("WARNING: No experiments found")
            return
        num_runs = 0 
        for j,exp in enumerate(exps):
            num_runs += self._build_experiment(exp.experiment_id, j, len(exps))
        print("Total: Found {} experiments with {} runs".format(len(exps),num_runs))

    def build_experiment(self, experiment_id, idx=None, num_exps=None):
        spark.sql("create database if not exists "+self.database)
        return self._build_experiment(experiment_id, idx, num_exps)

    def build_experiments(self, exp_ids=[]):
        self._create_database()
        self._build_all_data(exp_ids)
        self._build_all_ddl()