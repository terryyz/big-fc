import json
import os
from typing import Iterable, Dict
import gzip
from datasets import load_dataset

def write_jsonl(
    filename: str, data: Iterable[Dict], append: bool = False, drop_builtin: bool = True
):
    """
    Writes an iterable of dictionaries to jsonl
    """
    if append:
        mode = "ab"
    else:
        mode = "wb"
    filename = os.path.expanduser(filename)
    if filename.endswith(".gz"):
        with open(filename, mode) as fp:
            with gzip.GzipFile(fileobj=fp, mode="wb") as gzfp:
                for x in data:
                    if drop_builtin:
                        x = {k: v for k, v in x.items() if not k.startswith("_")}
                    gzfp.write((json.dumps(x) + "\n").encode("utf-8"))
    else:
        with open(filename, mode) as fp:
            for x in data:
                if drop_builtin:
                    x = {k: v for k, v in x.items() if not k.startswith("_")}
                fp.write((json.dumps(x) + "\n").encode("utf-8"))

def get_apis():
    with open("apis_info.jsonl", "r") as f:
        return {i: json.loads(line) for i, line in enumerate(f)}
    
def load_api2task():
    with open("api2task.json", "r") as f:
        return json.load(f)

def load_example():
    ds = load_dataset("bigcode/bigcodebench-hard", split="v0.1.0_hf")
    ds_dict = dict()
    for sample in ds:
        ds_dict[sample["task_id"]] = sample["code_prompt"] + sample["canonical_solution"]
    return ds_dict