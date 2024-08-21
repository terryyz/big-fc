from bigcodebench.data import get_bigcodebench
import os
import shutil
import json
import argparse

with open("code2apis.json", "r") as f:
    code2apis = json.load(f)

def replace_api_key_in_code(code, code2api):
    lines = code.split('\n')
    for pos, apis in code2api.items():
        line, col = map(int, pos.strip('()').split(', '))
        for api in apis:
            api_key = api['api_key']
            # api_call = api['api_call']
            line_content = lines[line - 1]
            start_index = line_content.find(api_key)
            if start_index != -1:
                end_index = start_index + len(api_key)
                lines[line - 1] = line_content[:start_index] + f"&&{api_key}&&" + line_content[end_index:]
    return '\n'.join(lines)

def inspection(split, subset, save_path="ground_truth", in_place=False):
    """
    Write a series of files for each task into a directory.
    
    Each Directory Structure:
    -- task_id
        -- ground_truth.py: prompt + canonical_solution
        -- completion.py: prompt + completion
        -- execution_trace.txt: execution trace
    """
    problems = get_bigcodebench(subset=subset)
    os.makedirs(save_path, exist_ok=True)
    for task_id, results in problems.items():
        apis = code2apis[task_id]
        task_id = task_id.split("/")[-1]
        task_path = os.path.join(save_path, task_id)
        task_id_data = results
        with open(task_path+".py", "w") as f:
            code_prompt = task_id_data[f"code_prompt"]
            solution = task_id_data["canonical_solution"]
            if task_id == "37":
                code_prompt = "import pandas as pd\n" + code_prompt
            code = replace_api_key_in_code(code_prompt + solution, apis)
            f.write(code)
            # f.write("\n\n")
if __name__ == "__main__":
    inspection(split="complete", subset="hard", save_path="ground_truth", in_place=False)