import json
from utils import write_jsonl, get_apis



def dedup_data(data):
    seen = set()
    deduplicated = []
    for item in data:
        item_tuple = tuple(sorted(item.items()))
        if item_tuple not in seen:
            seen.add(item_tuple)
            deduplicated.append(item)
    return deduplicated

def read_jsonl(filename):
    with open(filename, "r") as f:
        return [json.loads(line) for line in f]

def validate_type(data, apis):
    valid_data = []
    _ids = set()
    for item in data:
        if "error" in apis[item["api_id"]]:
            valid_data.append(item)
        elif apis[item["api_id"]]["type"] == json.loads(item["synthesis"])["type"]:
            valid_data.append(item)
        _ids.add(item["api_id"])
    assert len(apis) == len(_ids), f"Missing {set(apis.keys()) - _ids}"
    return valid_data

if __name__ == "__main__":
    apis = get_apis()
    pos_data = read_jsonl("positive--deepseek-ai--DeepSeek-Coder-V2-Lite-Instruct--vllm-0.8-10.jsonl")
    write_jsonl("positive-dedup.jsonl", dedup_data(pos_data))
    write_jsonl("positive-dedup.jsonl", validate_type(dedup_data(pos_data), apis))
    neg_data = read_jsonl("negative--deepseek-ai--DeepSeek-Coder-V2-Lite-Instruct--vllm-0.8-10.jsonl")
    write_jsonl("negative-dedup.jsonl", dedup_data(neg_data))