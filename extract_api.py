import ast


def extract_apis(code):
    tree = ast.parse(code)
    api_dict = []
    imported_modules = {}
    imported_names = {}

    class ApiExtractor(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                module_name = alias.name
                alias_name = alias.asname or alias.name
                imported_modules[alias_name] = module_name
            self.generic_visit(node)

        def visit_ImportFrom(self, node):
            module = node.module
            if module:
                for alias in node.names:
                    full_name = f'{module}.{alias.name}'
                    alias_name = alias.asname or alias.name
                    imported_names[alias_name] = full_name
            self.generic_visit(node)

        def visit_Attribute(self, node):
            attrs = []
            current = node
            while isinstance(current, ast.Attribute):
                attrs.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                attrs.append(current.id)
                attrs.reverse()
                base = attrs[0]
                if base in imported_modules:
                    api_call = f"{imported_modules[base]}.{'.'.join(attrs[1:])}"
                    self.add_api_call(api_call, node)
                elif base in imported_names:
                    api_call = f"{imported_names[base]}.{'.'.join(attrs[1:])}" if len(attrs) > 1 else imported_names[base]
                    self.add_api_call(api_call, node)
                else:
                    # Track object method calls
                    parent = self.get_parent(node)
                    if isinstance(parent, ast.Call) and parent.func == node:
                        obj_init = self.get_object_initialization(base)
                        if obj_init:
                            method_call = f"{'.'.join(attrs[1:])}{self.get_call_args(parent)}"
                            api_call = f"{obj_init}.{method_call}"
                            self.add_api_call(api_call, node)
            self.generic_visit(node)

        def add_api_call(self, api_call, node):
            parent = self.get_parent(node)
            if isinstance(parent, ast.Call) and parent.func == node:
                args = self.get_call_args(parent)
                if not api_call.endswith(args):
                    api_call += args
            
            # Remove duplicate object initializations
            parts = api_call.split('.')
            if len(parts) > 2 and '(' in parts[1]:
                api_call = f"{parts[0]}.{parts[1]}.{'.'.join(parts[2:])}"
            
            # Only add the API call if it's actually used (i.e., part of a Call node)
            if isinstance(parent, ast.Call):
                if api_call not in api_dict:
                    api_dict.append(api_call)

        def get_object_initialization(self, obj_name):
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == obj_name:
                            if isinstance(node.value, ast.Call):
                                return f"{ast.unparse(node.value.func)}{self.get_call_args(node.value)}"
            return None

        def visit_Name(self, node):
            if node.id in imported_modules:
                api_call = imported_modules[node.id]
                if '.' in api_call:
                    self.add_api_call(api_call, node)
            elif node.id in imported_names:
                api_call = imported_names[node.id]
                self.add_api_call(api_call, node)
            self.generic_visit(node)

        def visit_Call(self, node):
            self.visit(node.func)
            for arg in node.args:
                self.visit(arg)
            for keyword in node.keywords:
                self.visit(keyword.value)
            
        def get_parent(self, node):
            for parent in ast.walk(tree):
                for child in ast.iter_child_nodes(parent):
                    if child == node:
                        return parent
            return None

        def get_call_args(self, call_node):
            args = []
            for arg in call_node.args:
                args.append(ast.unparse(arg))
            for keyword in call_node.keywords:
                args.append(f"{keyword.arg}={ast.unparse(keyword.value)}")
            return '(' + ', '.join(args) + ')'

    ApiExtractor().visit(tree)
    return api_dict

if __name__ == "__main__":
    import json
    from tqdm import tqdm

    # dataset = load_dataset("bigcode/bigcodebench-hard", split="v0.1.0_hf")
    with open("hard.jsonl") as f:
        dataset = [json.loads(line) for line in f]
    apis = []
    api_dict = dict()
    api2task = dict()
    for item in tqdm(dataset[:]):
        task_id = item["task_id"]
        if task_id != "BigCodeBench/139":
            continue
        complete_prompt = item["complete_prompt"]
        canonical_solution = item["canonical_solution"]
        tmp_apis = sorted(set(extract_apis(complete_prompt+canonical_solution)), key=lambda x: len(x))
        # print(tmp_apis)
        filtered_apis = []
        for api in tmp_apis:
            # if not any(other_api.startswith(api) for other_api in tmp_apis if api != other_api):
            #     filtered_apis.append(api)
            flg = True
            for other_api in filtered_apis:
                if api.startswith(other_api) and api.endswith(')'):
                    filtered_apis.append(api.replace(other_api, other_api.split("(")[0]))
                    # print(api, other_api)
                    flg = False
                    break
            if flg:
                filtered_apis.append(api)
        if len(filtered_apis) < 3:
            print(task_id)
        for api in filtered_apis:
            api2task.setdefault(api, []).append(task_id)
        
        api_dict[task_id] = sorted(filtered_apis, key=lambda x: x.split('.')[0])
        apis.extend(filtered_apis)
    
    with open("apis.json", "w") as f:
        json.dump(api_dict, f, indent=4)
    
    with open("api2task.json", "w") as f:
        json.dump(api2task, f, indent=4)
    
    sorted_apis = sorted(list(set(apis)), key=lambda x: x.split('.')[0])
    with open("apis.txt", "w") as f:
        for api in sorted_apis:
            f.write(api + "\n")