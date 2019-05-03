
import pandas as pd
from mlflow_fun.common.mlflow_smart_client import MlflowSmartClient

class PandasDataframeBuilder(object):
    def __init__(self):
        self.smart_client = MlflowSmartClient()

    def build_dataframe(self, experiment_id):
        runs = self.smart_client.list_runs_flat(experiment_id)
        if len(runs) == 0:
            print("WARNING: No runs for experiment {}".format(experiment_id))
            return None
        return pd.DataFrame.from_dict(runs)

    def get_best_run(self, experiment_id, metric, ascending=True):
        if not metric.startswith("_m_"): metric = "_m_"+metric
        df = self.build_dataframe(experiment_id)
        if df is None: 
            return None
        if metric not in df:
            return []
        df = df[['run_uuid',metric]]
        df = df.sort_values(metric,ascending=ascending)
        best = df.iloc[0]
        return (best[0],best[1])
    
