"""
Imports a run from a directory of zip file.
"""

import os
import time
import mlflow
from mlflow_fun.export_import import utils
from mlflow_fun.export_import import mk_local_path

class RunImporter(object):
    def __init__(self, mlflow_client=None, use_src_user_id=False, import_mlflow_tags=False):
        self.client = mlflow_client or mlflow.tracking.MlflowClient()
        self.use_src_user_id = use_src_user_id
        self.import_mlflow_tags = import_mlflow_tags

    def import_run(self, exp_name, input):
        print("Importing run into experiment '{}' from '{}'".format(exp_name, input),flush=True)
        if input.endswith(".zip"):
            return self.import_run_from_zip(exp_name, input)
        else:
            return self.import_run_from_dir(exp_name, input)

    def import_run_from_zip(self, exp_name, zip_file):
        utils.unzip_directory(zip_file, exp_name, self.import_run_from_dir)
        return "run_id_TODO"

    def import_run_from_dir(self, dst_exp_name, src_run_id):
        mlflow.set_experiment(dst_exp_name)
        dst_exp = self.client.get_experiment_by_name(dst_exp_name)
        #print("Experiment name:",dst_exp_name)
        #print("Experiment ID:",dst_exp.experiment_id)
        src_run_path = os.path.join(src_run_id,"run.json")
        run_dct = utils.read_json_file(src_run_path)
        with mlflow.start_run() as run:
            run_id = run.info.run_id
            self.import_run_data(run_dct,run.info.run_id, run_dct['info']['user_id'])
            path = os.path.join(src_run_id,"artifacts")
            mlflow.log_artifacts(mk_local_path(path))
        return run_id

    def import_run_data(self, run_dct, run_id, src_user_id):
        from mlflow.entities import Metric, Param, RunTag
        now = int(time.time()+.5)
        params = [ Param(k,v) for k,v in run_dct['params'].items() ]
        metrics = [ Metric(k,v,now,0) for k,v in run_dct['metrics'].items() ] # TODO: missing timestamp and step semantics?
        #tags = [ RunTag(k,str(v)) for k,v in run_dct['tags'].items() ]
        tags = utils.create_tags_for_mlflow_tags(tags, self.import_mlflow_tags) # XX
        utils.set_dst_user_id(tags, src_user_id, self.use_src_user_id)
        self.client.log_batch(run_id, metrics, params, tags)

if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--input", dest="input", help="Input path - directory or zip file", required=True)
    parser.add_argument("--experiment_name", dest="experiment_name", help="Destination experiment_name", required=True)
    parser.add_argument("--use_src_user_id", dest="use_src_user_id", help="Use source user ID", default=False, action='store_true')
    parser.add_argument("--import_mlflow_tags", dest="import_mlflow_tags", help="Import mlflow tags", default=False, action='store_true')
    args = parser.parse_args()
    print("Options:")
    for arg in vars(args):
        print("  {}: {}".format(arg,getattr(args, arg)))
    importer = RunImporter(None,args.use_src_user_id, import_mlflow_tags)
    importer.import_run(args.experiment_name, args.input)
