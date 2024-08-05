import ast

def extract_apis(code):
    tree = ast.parse(code)
    api_list = []
    imported_modules = {}
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
                if optional_vars and isinstance(optional_vars, ast.Name):
                    context_name = ast.unparse(context_expr)
                    alias_name = optional_vars.id
                    variable_map[alias_name] = context_name.split('(', -1)[0]
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
                    self.add_api_call(api_call, node, 'attribute')
                elif base in imported_names:
                    api_call = f"{imported_names[base]}.{'.'.join(attrs[1:])}" if len(attrs) > 1 else imported_names[base]
                    self.add_api_call(api_call, node, 'attribute')
                elif base in variable_map:
                    api_call = variable_map[base]
                    api_call = f"{api_call}.{'.'.join(attrs[1:])}"
                    attrs = api_call.split('.')
                    base = attrs[0]
                    if base in imported_modules:
                        api_call = f"{imported_modules[base]}.{'.'.join(attrs[1:])}"
                    elif base in imported_names:
                        api_call = f"{imported_names[base]}.{'.'.join(attrs[1:])}"
                    self.add_api_call(api_call, node, 'attribute')
                else:
                    # Handle direct module attributes like np.pi
                    if base in imported_modules:
                        api_call = f"{imported_modules[base]}.{'.'.join(attrs[1:])}"
                        self.add_api_call(api_call, node, 'attribute')
                    elif base in imported_names:
                        api_call = f"{imported_names[base]}.{'.'.join(attrs[1:])}"
                        self.add_api_call(api_call, node, 'attribute')
                    else:
                        parent = self.get_parent(node)
                        if isinstance(parent, ast.Call) and parent.func == node:
                            obj_init = self.get_object_initialization(base)
                            if obj_init:
                                method_call = f"{'.'.join(attrs[1:])}{self.get_call_args(parent)}"
                                api_call = f"{obj_init}.{method_call}"
                                self.add_api_call(api_call, node, 'method')
                            else:
                                self.add_api_call(full_attr, node, 'attribute')
                        else:
                            self.add_api_call(full_attr, node, 'attribute')
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
                            self.add_api_call(api_call, node, 'attribute')
                        elif base_name in imported_modules:
                            api_call = f"{imported_modules[base_name]}.{base.attr}['{ast.unparse(subscript.slice)}']"
                            self.add_api_call(api_call, node, 'attribute')
                        elif base_name in imported_names:
                            api_call = f"{imported_names[base_name]}.{base.attr}['{ast.unparse(subscript.slice)}']"
                            self.add_api_call(api_call, node, 'attribute')
            elif isinstance(node.targets[0], ast.Tuple):
                for index, target in enumerate(node.targets[0].elts):
                    if isinstance(target, ast.Name):
                        if isinstance(node.value, ast.Call):
                            api_call = ast.unparse(node.value.func)
                            if api_call in imported_modules:
                                api_call = imported_modules[api_call]
                            elif api_call in imported_names:
                                api_call = imported_names[api_call]
                            variable_map[target.id] = f"{api_call}[{index}]"
                            self.object_creations[target.id] = index
            elif isinstance(node.value, ast.Call):
                api_call = ast.unparse(node.value.func)
                if api_call in imported_modules:
                    api_call = imported_modules[api_call]
                elif api_call in imported_names:
                    api_call = imported_names[api_call]
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        variable_map[target.id] = api_call
                    elif isinstance(target, ast.Tuple):
                        for index, elt in enumerate(target.elts):
                            if isinstance(elt, ast.Name):
                                variable_map[elt.id] = api_call
                                self.object_creations[elt.id] = index

            elif isinstance(node.targets[0], ast.Attribute):
                attr = node.targets[0]
                if isinstance(attr.value, ast.Name):
                    base = attr.value.id
                    if base in variable_map:
                        api_call = f"{variable_map[base]}.{attr.attr}"
                        self.add_api_call(api_call, node, 'attribute')
                    else:
                        # Handle cases where the base is a direct import or class instance
                        if base in imported_modules:
                            api_call = f"{imported_modules[base]}.{attr.attr}"
                            self.add_api_call(api_call, node, 'attribute')
                        elif base in imported_names:
                            api_call = f"{imported_names[base]}.{attr.attr}"
                            self.add_api_call(api_call, node, 'attribute')
                # Handle nested attributes like app.config['MAIL_SERVER']
                if isinstance(attr.value, ast.Attribute):
                    nested_attr = attr.value
                    if isinstance(nested_attr.value, ast.Name):
                        nested_base = nested_attr.value.id
                        if nested_base in variable_map:
                            api_call = f"{variable_map[nested_base]}.{nested_attr.attr}.{attr.attr}"
                            self.add_api_call(api_call, node, 'attribute')
                        else:
                            # Handle cases where the nested base is a direct import or class instance
                            if nested_base in imported_modules:
                                api_call = f"{imported_modules[nested_base]}.{nested_attr.attr}.{attr.attr}"
                                self.add_api_call(api_call, node, 'attribute')
                            elif nested_base in imported_names:
                                api_call = f"{imported_names[nested_base]}.{nested_attr.attr}.{attr.attr}"
                                self.add_api_call(api_call, node, 'attribute')

            self.generic_visit(node)

        def add_api_call(self, api_call, node, api_type):
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
            if isinstance(parent, ast.Call) or isinstance(parent, ast.Subscript) or isinstance(node, ast.Attribute):
                if api_call not in api_list:
                    api_list.append({'api': api_call, 'type': api_type})
                    
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                base = node.value.id
                if base in variable_map and '[' in variable_map[base]:
                    api_call = f"{variable_map[base]}.{node.attr}"
                    if api_call not in api_list:
                        api_list.append({'api': api_call, 'type': api_type})
        
        def visit_Name(self, node):
            if node.id in imported_modules:
                api_call = imported_modules[node.id]
                if '.' in api_call:
                    self.add_api_call(api_call, node, 'attribute')
            elif node.id in imported_names:
                api_call = imported_names[node.id]
                self.add_api_call(api_call, node, 'attribute')
            self.generic_visit(node)

        def visit_Call(self, node):
            self.visit(node.func)
            for arg in node.args:
                self.visit(arg)
            for keyword in node.keywords:
                self.visit(keyword.value)
            # Identify the function or method call
            if isinstance(node.func, ast.Attribute):
                self.add_api_call(ast.unparse(node.func), node, 'method')
            elif isinstance(node.func, ast.Name):
                self.add_api_call(node.func.id, node, 'function')
            
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
    return api_list

sample_code = """
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import a
# Constants
COLUMNS = ['Date', 'Value']
def task_func(df, plot=False):
    if not isinstance(df, pd.DataFrame) or 'Value' not in df or 'Date' not in df or len(df.index) == 0:
        raise ValueError()

    df['Date'] = pd.to_datetime(df['Date'])
    df = pd.concat([df['Date'], df['Value'].apply(pd.Series)], axis=1)

    corr_df = df.iloc[:, 1:].corr()
    ggg,ddd = a.task_func(df)
    ggg.to_csv("ggg.csv")
    if plot:
        plt.figure()
        heatmap = sns.heatmap(corr_df, annot=True, cmap='coolwarm')
        plt.title('Correlation Heatmap')
        return corr_df, heatmap

    return corr_df
"""

api_list = extract_apis(sample_code)
print("API Dictionary:", api_list)