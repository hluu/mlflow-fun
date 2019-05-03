from __future__ import print_function
from pyspark.sql import SparkSession, Row
from collections import OrderedDict
import mlflow
from mlflow_fun.common import mlflow_utils

def get_best_run(experiment_id, metric, ascending=True, which="fast"):
    if not metric.startswith("_m_"): 
        metric = "_m_" + metric
    builder = get_data_frame_builder(which)
    df = builder.build_dataframe(experiment_id)
    df = df.select("run_uuid", metric).filter("{} is not NULL".format(metric)).sort(metric,ascending=ascending)
    row = df.first()
    return (row[0],row[1])

def get_data_frame_builder(which="slow"):
    return SlowDataframeBuilder() if which == "slow" else FastDataframeBuilder()

class BaseDataframeBuilder(object):
    def build_dataframe(self, experiment_id, idx=None, num_exps=None):
        (df,n) = self.build_dataframe_(experiment_id, idx, num_exps)
        return df

''' Calls MLflow client '''
class SlowDataframeBuilder(BaseDataframeBuilder):
    def __init__(self, mlflow_client=None, spark=None, logmod=20):
        self.logmod = logmod 
        self.mlflow_client = mlflow_client 
        self.spark = spark 
        self.mlflow_client = mlflow_client 
        if mlflow_client is None:
            self.mlflow_client = mlflow.tracking.MlflowClient()
            mlflow_utils.dump_mlflow_info()
        if spark is None:
            self.spark = SparkSession.builder.appName("mlflow_metrics").enableHiveSupport().getOrCreate()
        print("logmod:",logmod)

    def _strip_underscores(self, obj):
        return { k[1:]:v for (k,v) in obj.__dict__.items() }

    def build_dataframe_(self, experiment_id, idx=None, num_exps=None):
        infos = self.mlflow_client.list_run_infos(experiment_id)
        if idx is None:
            print("Experiment {} has {} runs".format(experiment_id,len(infos)))
        else:
            print("{}/{}: Experiment {} has {} runs".format((1+idx),num_exps,experiment_id,len(infos)))
        if len(infos) == 0:
            print("WARNING: No runs for experiment {}".format(experiment_id))
            return (None,0)
        rows = []
        for j,info in enumerate(infos):
            if j%self.logmod==0: print("  run {}/{} of experiment {}".format(j,len(infos),experiment_id))
            run = self.mlflow_client.get_run(info.run_uuid)
            dct = self._strip_underscores(info)
            params = { "_p_"+x.key:x.value for x in run.data.params }
            metrics = { "_m_"+x.key:x.value for x in run.data.metrics }
            tags = { "_t_"+x.key:x.value for x in run.data.tags }
            dct.update(params)
            dct.update(metrics)
            dct.update(tags)
            rows.append(dct)
        df = self.spark.createDataFrame(rows)
        return (df,len(infos))

''' Calls REST client runs/search endpoint '''
class FastDataframeBuilder(BaseDataframeBuilder):
    def __init__(self, mlflow_smart_client=None, spark=None, logmod=20):
        from mlflow_fun.common.mlflow_smart_client import MlflowSmartClient
        self.logmod = logmod 
        if mlflow_smart_client is None:
            mlflow_smart_client = MlflowSmartClient()
        self.mlflow_smart_client = mlflow_smart_client 

        self.spark = spark 
        if spark is None:
            self.spark = SparkSession.builder.appName("mlflow_metrics").enableHiveSupport().getOrCreate()
        print("logmod:",logmod)

    def build_dataframe_(self, experiment_id, idx=None, num_exps=None):
        runs = self.mlflow_smart_client.list_runs_flat(experiment_id)
        if len(runs) == 0:
            print("WARNING: No runs for experiment {}".format(experiment_id))
            return (None,0)
        df = self.spark.createDataFrame(runs)
        return (df,len(runs))
