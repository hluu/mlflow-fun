import os
import shutil
import zipfile
import json
import time
import mlflow
from . import mk_local_path

prefix = "mlflow_tools.export"

# Databricks tags that cannot be set
dbx_skip_tags = set([ "mlflow.user" ])

def create_tags(client, run, log_source_info):
    tags = run.data.tags.copy()
    for tag_key in dbx_skip_tags:
        tags.pop(tag_key, None)

    if not log_source_info:
        return tags

    uri = mlflow.tracking.get_tracking_uri()
    tags[prefix+".tracking_uri"] = uri
    dbx_host = os.environ.get("DATABRICKS_HOST",None)
    if dbx_host is not None:
        tags[prefix+".DATABRICKS_HOST"] = dbx_host
    now = int(time.time()+.5)
    snow = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now))
    tags[prefix+".timestamp"] = str(now)
    tags[prefix+".timestamp_nice"] = snow

    tags[prefix+".run_id"] =  str(run.info.run_id)
    tags[prefix+".experiment_id"] = run.info.experiment_id
    exp = client.get_experiment(run.info.experiment_id)
    tags[prefix+".experiment_name"] = exp.name
    tags[prefix+".user_id"] = run.info.user_id

    return tags

def get_now_nice():
    now = int(time.time()+.5)
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now))

def strip_underscores(obj):
    return { k[1:]:v for (k,v) in obj.__dict__.items() }

def write_json_file(fs, path, dct):
    fs.write(path, json.dumps(dct,indent=2)+"\n")

def write_file(path, content):
    with open(mk_local_path(path), 'wb') as f:
        f.write(content)

def read_json_file(path):
    with open(mk_local_path(path), "r") as f:
        return json.loads(f.read())

def zip_directory(zip_file, dir):
    zipf = zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(dir):
        for file in files:
            full_path = os.path.join(root, file)
            relative_path = full_path.replace(dir+"/","")
            zipf.write(full_path,relative_path)
    zipf.close()

def unzip_directory(zip_file, exp_name, funk):
    import tempfile
    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(zip_file, "r") as f:
            f.extractall(temp_dir)
        funk(exp_name, temp_dir)
    finally:
        shutil.rmtree(temp_dir)

def string_to_list(list_as_string):
    lst = list_as_string.split(",")
    if "" in lst: list.remove("")
    return lst

def get_user_id():
    from mlflow.tracking.context.default_context import _get_user
    return _get_user()
