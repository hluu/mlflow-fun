""" 
Copies a run from one MLflow server to another.
"""

import time
import mlflow
from mlflow_fun.export_import import utils
from mlflow_fun.export_import import BaseCopier, create_client, add_repr_to_MlflowClient
print("MLflow Version:", mlflow.version.VERSION)
print("MLflow Tracking URI:", mlflow.get_tracking_uri())

class RunCopier(BaseCopier):
    def __init__(self, src_client, dst_client, export_metadata_tags=False, use_src_user_id=False,  import_mlflow_tags=False):
        super().__init__(src_client, dst_client)
        self.export_metadata_tags = export_metadata_tags
        self.use_src_user_id = use_src_user_id
        self.import_mlflow_tags = import_mlflow_tags

    def copy_run(self, src_run_id, dst_exp_name):
        print("src_run_id:",src_run_id)
        dst_exp = self.get_experiment(self.dst_client,dst_exp_name)
        print("  dst_exp.name:",dst_exp.name)
        print("  dst_exp.id:",dst_exp.experiment_id)
        self._copy_run(src_run_id, dst_exp.experiment_id)

    def _copy_run(self, src_run_id, dst_experiment_id):
        src_run = self.src_client.get_run(src_run_id)
        dst_run = self.dst_client.create_run(dst_experiment_id) # NOTE: does not set user_id; is 'unknown'
        self._copy_run_data(src_run, dst_run.info.run_id)
        local_path = self.src_client.download_artifacts(src_run_id,"")
        self.dst_client.log_artifacts(dst_run.info.run_id,local_path)

    def _copy_run_data(self, src_run, dst_run_id):
        from mlflow.entities import Metric, Param, RunTag
        now = int(time.time()+.5)
        params = [ Param(k,v) for k,v in src_run.data.params.items() ]
        metrics = [ Metric(k,v,now,0) for k,v in src_run.data.metrics.items() ] # TODO: timestamp and step semantics?
        tags = utils.create_tags_for_metadata(self.src_client, src_run, self.export_metadata_tags)
        #tags = [ RunTag(k,v) for k,v in tags.items() ]
        tags = utils.create_tags_for_mlflow_tags(tags, self.import_mlflow_tags) # XX
        utils.set_dst_user_id(tags, src_run.info.user_id, self.use_src_user_id)
        self.dst_client.log_batch(dst_run_id, metrics, params, tags)

if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--src_uri", dest="src_uri", help="Source MLFLOW API URL", default=None)
    parser.add_argument("--dst_uri", dest="dst_uri", help="Destination MLFLOW API URL", default=None)
    parser.add_argument("--src_run_id", dest="src_run_id", help="Source run_id", required=True)
    parser.add_argument("--dst_experiment_name", dest="dst_experiment_name", help="Destination experiment_name", required=True)
    parser.add_argument("--export_metadata_tags", dest="export_metadata_tags", help="Export source run metadata tags", default=False, action='store_true')
    parser.add_argument("--use_src_user_id", dest="use_src_user_id", help="Use source user ID", default=False, action='store_true')
    parser.add_argument("--import_mlflow_tags", dest="import_mlflow_tags", help="Import mlflow tags", default=False, action='store_true')
    args = parser.parse_args()
    print("Options:")
    for arg in vars(args):
        print("  {}: {}".format(arg,getattr(args, arg)))
    src_client = create_client(args.src_uri)
    dst_client = create_client(args.dst_uri)
    print("  src_client:",src_client)
    print("  dst_client:",dst_client)
    copier = RunCopier(src_client, dst_client, args.export_metadata_tags, args.use_src_user_id, args.import_mlflow_tags)
    copier.copy_run(args.src_run_id, args.dst_experiment_name)
