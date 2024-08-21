import ast


def get_builtin_classes():
    import builtins
    builtin_classes = dict()
    for name in dir(builtins):
        obj = getattr(builtins, name)
        if isinstance(obj, type):
            builtin_classes[name] = name
    return builtin_classes

def extract_apis(code):
    tree = ast.parse(code)
    api_dict = {}
    imported_modules = get_builtin_classes()
    imported_names = {}
    variable_map = {}
    class_map = {}

    class ApiExtractor(ast.NodeVisitor):
        def __init__(self):
            self.current_object = None
            self.object_creations = {}
            self.class_stack = []
            self.method_stack = []
            self.self_class_map = {}

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

        def visit_With(self, node):
            for item in node.items:
                context_expr = item.context_expr
                optional_vars = item.optional_vars
                if isinstance(context_expr, ast.Call):
                    api_call = ast.unparse(context_expr)
                    base = api_call.split('(')[0].split('.')
                    for i in range(len(base)):
                        new_base = '.'.join(base[:i+1])
                        if new_base in imported_modules:
                            api_call = imported_modules[new_base] + api_call[len(new_base):]
                        elif new_base in imported_names:
                            api_call = imported_names[new_base] + api_call[len(new_base):]
                        elif new_base in variable_map:
                            api_call = variable_map[new_base] + api_call[len(new_base):]
                    self.add_api_call(api_call, api_call, context_expr)
                if optional_vars and isinstance(optional_vars, ast.Name):
                    context_name = ast.unparse(context_expr)
                    base = context_name.split('(')[0].split('.')
                    for i in range(len(base)):
                        new_base = '.'.join(base[:i+1])
                        if new_base in imported_modules:
                            context_name = imported_modules[new_base] + context_name[len(new_base):]
                        elif new_base in imported_names:
                            context_name = imported_names[new_base] + context_name[len(new_base):]
                        elif new_base in variable_map:
                            context_name = variable_map[new_base] + context_name[len(new_base):]
                    alias_name = optional_vars.id
                    variable_map[alias_name] = context_name.split('(', 1)[0]
            self.generic_visit(node)
        
        def get_object_initialization(self, obj_name):
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == obj_name:
                            if isinstance(node.value, ast.Call):
                                return f"{ast.unparse(node.value.func)}{self.get_call_args(node.value)}"
            return None
        
        def visit_ClassDef(self, node):
            self.class_stack.append(node.name)
            if node.bases:
                base = node.bases[0]
                if isinstance(base, ast.Attribute):
                    base_name = ast.unparse(base)
                    class_map[node.name] = base_name
                elif isinstance(base, ast.Name):
                    base_name = base.id
                    if base_name in imported_names:
                        class_map[node.name] = imported_names[base_name]
                    elif base_name in imported_modules:
                        class_map[node.name] = imported_modules[base_name]
            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(self, node):
            self.method_stack.append(node.name)
            self.generic_visit(node)
            self.method_stack.pop()

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
                full_attr = '.'.join(attrs)
                if base == 'self' and self.class_stack:
                    base = self.class_stack[-1]
                    if base in class_map:
                        full_attr = f"{class_map[base]}.{'.'.join(attrs[1:])}"
                    else:
                        full_attr = f"{base}.{'.'.join(attrs[1:])}"
                if base in imported_modules:
                    api_call = f"{imported_modules[base]}.{'.'.join(attrs[1:])}"
                    self.add_api_call(api_call, full_attr, node)
                elif base in imported_names:
                    api_call = f"{imported_names[base]}.{'.'.join(attrs[1:])}" if len(attrs) > 1 else imported_names[base]
                    self.add_api_call(api_call, full_attr, node)
                elif base in variable_map:
                    api_call = variable_map[base]
                    api_call = f"{api_call}.{'.'.join(attrs[1:])}"
                    attrs = api_call.split('.')
                    base = attrs[0]
                    if base in imported_modules:
                        api_call = f"{imported_modules[base]}.{'.'.join(attrs[1:])}"
                    elif base in imported_names:
                        api_call = f"{imported_names[base]}.{'.'.join(attrs[1:])}"
                    self.add_api_call(api_call, full_attr, node)
                else:
                    # Handle direct module attributes like np.pi
                    if base in imported_modules:
                        api_call = f"{imported_modules[base]}.{'.'.join(attrs[1:])}"
                        self.add_api_call(api_call, full_attr, node)
                    elif base in imported_names:
                        api_call = f"{imported_names[base]}.{'.'.join(attrs[1:])}"
                        self.add_api_call(api_call, full_attr, node)
                    else:
                        parent = self.get_parent(node)
                        if isinstance(parent, ast.Call) and parent.func == node:
                            obj_init = self.get_object_initialization(base)
                            if obj_init:
                                method_call = f"{'.'.join(attrs[1:])}{self.get_call_args(parent)}"
                                api_call = f"{obj_init}.{method_call}"
                                self.add_api_call(api_call, full_attr, node)
                            else:
                                self.add_api_call(full_attr, full_attr, node)
                        else:
                            self.add_api_call(full_attr, full_attr, node)
            self.generic_visit(node)
        
        def visit_Assign(self, node):
            if isinstance(node.targets[0], ast.Subscript):
                subscript = node.targets[0]
                if isinstance(subscript.value, ast.Attribute):
                    base = subscript.value
                    if isinstance(base.value, ast.Name):
                        base_name = base.value.id
                        if base_name in variable_map:
                            api_call = f"{variable_map[base_name]}.{base.attr}['{ast.unparse(subscript.slice)}']"
                            self.add_api_call(api_call, api_call, node)
                        elif base_name in imported_modules:
                            api_call = f"{imported_modules[base_name]}.{base.attr}['{ast.unparse(subscript.slice)}']"
                            self.add_api_call(api_call, api_call, node)
                        elif base_name in imported_names:
                            api_call = f"{imported_names[base_name]}.{base.attr}['{ast.unparse(subscript.slice)}']"
                            self.add_api_call(api_call, api_call, node)
            elif isinstance(node.targets[0], ast.Tuple):
                for index, target in enumerate(node.targets[0].elts):
                    if isinstance(target, ast.Name):
                        if isinstance(node.value, ast.Call):
                            api_call = ast.unparse(node.value.func)
                            parts = api_call.split('.')
                            base = parts[0]
                            attr = '.' + '.'.join(parts[1:]) if len(parts) > 1 else ''
                            if base in imported_modules:
                                api_call = imported_modules[base]+attr
                            elif base in imported_names:
                                api_call = imported_names[base]+attr
                            args = self.get_call_args(node.value)
                            api_call += args
                            variable_map[target.id] = f"{api_call}[{index}]"
                            self.object_creations[target.id] = index
            elif isinstance(node.value, ast.Call):
                # Extract the full call including arguments
                api_call = ast.unparse(node.value)
                base = api_call.split('(')[0].split('.')
                # print(api_call, base, variable_map)
                for i in range(len(base)):
                    new_base = '.'.join(base[:i+1])
                    if new_base in imported_modules:
                        api_call = imported_modules[new_base] + api_call[len(new_base):]
                    elif new_base in imported_names:
                        api_call = imported_names[new_base] + api_call[len(new_base):]
                    elif new_base in variable_map:
                        api_call = variable_map[new_base] + api_call[len(new_base):]
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        variable_map[target.id] = api_call
                        # print(target.id,api_call)
                        # print(variable_map)
                    elif isinstance(target, ast.Tuple):
                        for index, elt in enumerate(target.elts):
                            if isinstance(elt, ast.Name):
                                variable_map[elt.id] = api_call
                                # print(variable_map)
                                self.object_creations[elt.id] = index

            elif isinstance(node.targets[0], ast.Attribute):
                attr = node.targets[0]
                if isinstance(attr.value, ast.Name):
                    base = attr.value.id
                    if base in variable_map:
                        api_call = f"{variable_map[base]}.{attr.attr}"
                        self.add_api_call(api_call, api_call, node)
                    else:
                        # Handle cases where the base is a direct import or class instance
                        if base in imported_modules:
                            api_call = f"{imported_modules[base]}.{attr.attr}"
                            self.add_api_call(api_call, api_call, node)
                        elif base in imported_names:
                            api_call = f"{imported_names[base]}.{attr.attr}"
                            self.add_api_call(api_call, api_call, node)
                # Handle nested attributes like app.config['MAIL_SERVER']
                if isinstance(attr.value, ast.Attribute):
                    nested_attr = attr.value
                    if isinstance(nested_attr.value, ast.Name):
                        nested_base = nested_attr.value.id
                        if nested_base in variable_map:
                            api_call = f"{variable_map[nested_base]}.{nested_attr.attr}.{attr.attr}"
                            self.add_api_call(api_call, api_call, node)
                        else:
                            # Handle cases where the nested base is a direct import or class instance
                            if nested_base in imported_modules:
                                api_call = f"{imported_modules[nested_base]}.{nested_attr.attr}.{attr.attr}"
                                self.add_api_call(api_call, api_call, node)
                            elif nested_base in imported_names:
                                api_call = f"{imported_names[nested_base]}.{nested_attr.attr}.{attr.attr}"
                                self.add_api_call(api_call, api_call, node)

            self.generic_visit(node)

        def add_api_call(self, api_call, full_attr, node):
            parent = self.get_parent(node)
            if isinstance(parent, ast.Call) and parent.func == node:
                args = self.get_call_args(parent)
                if not api_call.endswith(args):
                    api_call += args

            # Remove duplicate object initializations
            parts = api_call.split('.')
            if len(parts) > 2 and '(' in parts[1]:
                api_call = f"{parts[0]}.{parts[1]}.{'.'.join(parts[2:])}"
            # Add the API call if it's part of a Call node, Subscript node, or a direct attribute
            if isinstance(parent, ast.Call) or isinstance(parent, ast.Subscript) or isinstance(node, ast.Attribute) or isinstance(parent, ast.Assign):
                if full_attr not in api_dict:
                    api_dict[full_attr] = []
                # Ensure no duplicate API calls are added
                if not any(api['api_call'] == api_call for api in api_dict[full_attr]):
                    api_dict[full_attr].append({
                        'api_call': api_call,
                        'line': node.lineno,
                        'col_offset': node.col_offset
                    })
        
        def visit_Name(self, node):
            if node.id in imported_modules:
                api_call = imported_modules[node.id]
                if '.' in api_call:
                    self.add_api_call(api_call, node.id, node)
            elif node.id in imported_names:
                api_call = imported_names[node.id]
                self.add_api_call(api_call, node.id, node)
            self.generic_visit(node)

        def visit_Call(self, node):
            self.visit(node.func)
            for arg in node.args:
                self.visit(arg)
            for keyword in node.keywords:
                self.visit(keyword.value)
            # Handle chained method calls
            if isinstance(node.func, ast.Attribute):
                func_name = ast.unparse(node.func)
                parts = func_name.split('.')
                base = parts[0].split('(', 1)[0]
                if base in variable_map:
                    obj_init = variable_map[base]
                    method_call = f"{'.'.join(parts[1:])}{self.get_call_args(node)}"
                    api_call = f"{obj_init}.{method_call}"
                    self.add_api_call(api_call, func_name, node)
                elif base in imported_modules:
                    api_call = f"{imported_modules[base]}.{'.'.join(parts[1:])}{self.get_call_args(node)}"
                    self.add_api_call(api_call, func_name, node)
                elif base in imported_names:
                    api_call = f"{imported_names[base]}.{'.'.join(parts[1:])}{self.get_call_args(node)}"
                    self.add_api_call(api_call, func_name, node)
                
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
                if keyword.arg is not None:
                    args.append(f"{keyword.arg}={ast.unparse(keyword.value)}")
                else:
                    args.append(f"**{ast.unparse(keyword.value)}")
            return '(' + ', '.join(args) + ')'

    ae = ApiExtractor()
    ae.visit(tree)
    # print(api_dict)
    # filtered_api_dict = {k: v for k, v in api_dict.items() if any(api['api_call'].split('.')[0] in imported_modules or api['api_call'].split('.')[0] in imported_names for api in v)}
    imported_modules = set(imported_modules.values())
    imported_names = set(imported_names.values())
    # print(imported_modules)
    # print(imported_names)
    non_api_dict = {k: v for k, v in api_dict.items() for api in v if not any(api['api_call'].startswith(module) for module in imported_modules) and not any(api['api_call'].startswith(name) for name in imported_names)}
    # print(non_api_dict)
    api_dict = {k: v for k, v in api_dict.items() if k not in non_api_dict}
    
    # # Print the filtered APIs
    # for api_key, apis in filtered_api_dict.items():
    #     print(f"{api_key}:")
    #     for api in apis:
    #         print(f"  {api['api_call']} (line {api['line']}, col {api['col_offset']})")
    
    return api_dict, non_api_dict, variable_map


if __name__ == "__main__":
    import json
    from tqdm import tqdm

    # dataset = load_dataset("bigcode/bigcodebench-hard", split="v0.1.0_hf")
    with open("hard.jsonl") as f:
        dataset = [json.loads(line) for line in f]
    apis = []
    api_list = dict()
    api2task = dict()
    code2apis = dict()
    non_api_dict = dict()
    var2apis = dict()
    for item in tqdm(dataset[:]):
        task_id = item["task_id"]
        # print(task_id)
        # if task_id not in ["BigCodeBench/914", "BigCodeBench/1008", "BigCodeBench/1039", "BigCodeBench/1053"]:
        #     continue
        complete_prompt = item["code_prompt"]
        if task_id == "BigCodeBench/37":
            complete_prompt = "import pandas as pd\n" + complete_prompt
        if task_id == "BigCodeBench/590":
            complete_prompt = "import pandas as urllib\n" + complete_prompt
        canonical_solution = item["canonical_solution"]
        tmp_code2apis, tmp_non_api_dict, tmp_var2apis = extract_apis(complete_prompt+canonical_solution)
        tmp_pos2apis = dict()
        for api_key, _apis in tmp_code2apis.items():
            for api in _apis:
                tmp_pos2apis.setdefault(str((api['line'], api['col_offset'])), []).append({"api_key": api_key, "api_call": api['api_call']})
        
        # remove the api call with the same line and col_offset, but is the substring of another api call
        # for pos, _apis in tmp_pos2apis.items():
        #     for api in _apis:
        #         for other_api in _apis:
        #             if api['api_call'] != other_api['api_call'] and api['api_call'] in other_api['api_call']:
        #                 _apis.remove(api)
        for pos, _apis in tmp_pos2apis.items():
            longest_api = max(_apis, key=lambda x: len(x['api_call']))
            _apis[:] = [api for api in _apis if api['api_call'] == longest_api['api_call']]
        code2apis[task_id] = tmp_pos2apis
        var2apis[task_id] = tmp_var2apis
        non_api_dict[task_id] = tmp_non_api_dict
        all_apis = [api['api_call'] for _apis in tmp_code2apis.values() for api in _apis]
        tmp_apis = sorted(set(all_apis), key=lambda x: len(x), reverse=True)
        filtered_apis = []
        for api in tmp_apis:
            # if not any(other_api.startswith(api) for other_api in tmp_apis if api != other_api):
            #     filtered_apis.append(api)
            flg = True
            for other_api in filtered_apis:
                if other_api.startswith(api) and not api.endswith(')'):
                    # print(api, other_api)
                    filtered_apis.append(api.replace(other_api, other_api.split("(")[0]))
                    # print(api, other_api)
                    flg = False
                    break
            if flg:
                # print(api)
                filtered_apis.append(api)
        if len(filtered_apis) < 3:
            print(task_id)
        for api in filtered_apis:
            api2task.setdefault(api, []).append(task_id)
        # exit()
        api_list[task_id] = sorted(filtered_apis, key=lambda x: x.split('.')[0])
        apis.extend(filtered_apis)
    
    with open("code2apis.json", "w") as f:
        json.dump(code2apis, f, indent=4)
    with open("non_api_dict.json", "w") as f:
        json.dump(non_api_dict, f, indent=4)
    with open("var2apis.json", "w") as f:
        json.dump(var2apis, f, indent=4)
    with open("apis.json", "w") as f:
        json.dump(api_list, f, indent=4)
    
    with open("api2task.json", "w") as f:
        json.dump(api2task, f, indent=4)
    
    sorted_apis = sorted(list(set(apis)), key=lambda x: x.split('.')[0])
    with open("apis.txt", "w") as f:
        for api in sorted_apis:
            f.write(api + "\n")