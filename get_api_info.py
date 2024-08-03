import ast
import inspect
import importlib
import json
from tqdm import tqdm


def filter_unused_args(signature, api_call):
    # Extract arguments from the signature
    sig_args = [arg.strip() for arg in signature[1:-1].split(',') if arg.strip()]
    original_sig_args = sig_args.copy()

    try:
        call = ast.parse(api_call).body[0].value
        if isinstance(call, ast.Call):
            used_positional_args = set()
            used_keyword_args = set()

            # Map positional arguments from the API call to the signature
            for i, arg in enumerate(call.args):
                if i < len(sig_args):
                    used_positional_args.add(sig_args[i + 1].split(':')[0].split('=')[0].strip() if sig_args[0] == 'self' else sig_args[i].split(':')[0].split('=')[0].strip())

            # Collect keyword arguments from the API call
            used_keyword_args = {arg.arg for arg in call.keywords}

            used_args = used_positional_args.union(used_keyword_args)

            # Always retain 'self' if it's present
            if 'self' in sig_args:
                used_args.add('self')

            # Include *args and **kwargs if they are part of the call
            if any(arg.startswith('*') or arg.startswith('**') for arg in sig_args):
                if len(call.args) > len([arg for arg in sig_args if not arg.startswith('*')]):
                    used_args.update([arg for arg in sig_args if arg.startswith('*')])
                if len(call.keywords) > 0:
                    used_args.update([arg for arg in sig_args if arg.startswith('**')])

            # Filter arguments while maintaining original order
            filtered_args = [arg for arg in original_sig_args if arg.split(':')[0].split('=')[0].strip() in used_args]

            return f"({', '.join(filtered_args)})"
        else:
            return signature  # Return original if not a function call
    except Exception as e:
        return signature  # Return original if parsing fails

def get_api_info(api_call):
    def process_nested_call(call):
        if isinstance(call, ast.Attribute):
            return process_nested_call(call.value) + [call.attr]
        elif isinstance(call, ast.Name):
            return [call.id]
        else:
            return []
    try:
        parsed_call = ast.parse(api_call).body[0].value
        if isinstance(parsed_call, ast.Call):
            api_parts = process_nested_call(parsed_call.func)
        elif isinstance(parsed_call, ast.Attribute):
            api_parts = process_nested_call(parsed_call)
        else:
            api_parts = [parsed_call.id]
        api = ".".join(api_parts)
        module = None
        for i, part in enumerate(api_parts):
            if i == 0:
                module = importlib.import_module(part)
            else:
                module = getattr(module, part)
        result = {
            'name': api,
            'type': None,
            'signature': None,
            'short_docstring': None
        }
        if inspect.ismodule(module):
            result['type'] = 'module'
        elif inspect.isclass(module):
            result['type'] = 'class'
            try:
                result['signature'] = str(inspect.signature(module))
            except ValueError:
                pass
        elif callable(module):
            result['type'] = 'callable'
            try:
                result['signature'] = str(inspect.signature(module))
            except ValueError:
                pass
        else:
            result['type'] = 'constant'
            result['value'] = str(module)
        if result['signature'] and "(" in api_call:
            # print("Signature:", result['signature'])
            # print("API Call:", api_call)
            result['signature'] = filter_unused_args(result['signature'], api_call)
            # print("Filtered Signature:", result['signature'])
            # print("--------------------------------")
        result['short_docstring'] = (inspect.getdoc(module) or '').split('\n\n')[0]
        return result
    except ImportError as e:
        return {'name': api, 'error': f'Import error: {str(e)}'}
    except AttributeError as e:
        return {'name': api, 'error': f'Attribute error: {str(e)}'}
    except Exception as e:
        return {'name': api, 'error': str(e)}

def separate_api_calls(api_list):
    object_methods = []
    standalone_apis = []
    for api_call in api_list:
        parts = api_call.split('(')[0].split('.')
        if len(parts) > 1:
            try:
                module_name = parts[0]
                module = importlib.import_module(module_name)
                attr = getattr(module, parts[1])
                if inspect.isclass(attr):
                    object_methods.append(api_call)
                else:
                    standalone_apis.append(api_call)
            except (ImportError, AttributeError):
                standalone_apis.append(api_call)
        else:
            standalone_apis.append(api_call)
    return object_methods, standalone_apis

def process_object_methods(api_list):
    result = {}
    for api_call in api_list:
        parts = api_call.split('(')[0].split('.')
        base_obj = '.'.join(parts[:-1])
        method = parts[-1]
        if base_obj not in result:
            result[base_obj] = {"info": get_api_info(base_obj), "chains": {}}
        result[base_obj]["chains"][method] = get_api_info(api_call)
    return result

def process_standalone_apis(api_list):
    result = {}
    for api_call in api_list:
        api_info = get_api_info(api_call)
        result[api_info['name']] = {"info": api_info}
    return result

def combine_results(object_methods, standalone_apis):
    combined_result = {}
    for key, value in object_methods.items():
        combined_result[key] = value["info"]
        combined_result[key]["chains"] = value["chains"]
    for key, value in standalone_apis.items():
        combined_result[key] = value["info"]
    return combined_result

def remove_unnecessary_modules(combined_result):
    keys_to_remove = [key for key, value in combined_result.items() if value.get('type') == 'module']
    for key in keys_to_remove:
        del combined_result[key]
    return combined_result


# api_calls = [
#         "ftplib.FTP(ftp_server)",
#         "ftplib.FTP.cwd(ftp_dir)",
#         "ftplib.FTP.login(ftp_user, ftp_password)",
#         "ftplib.FTP.nlst()",
#         "ftplib.FTP.quit()",
#         "os.makedirs(download_dir)",
#         "os.path",
#         "os.path.exists(download_dir)",
#         "subprocess.call(command, shell=True)"
#     ]
# object_methods, standalone_apis = separate_api_calls(api_calls)
# processed_object_methods = process_object_methods(object_methods)
# processed_standalone_apis = process_standalone_apis(standalone_apis)
# api_info = combine_results(processed_object_methods, processed_standalone_apis)
# api_info = remove_unnecessary_modules(api_info)

# import json
# json_output = json.dumps(api_info, indent=2)
# print(json_output)


def process_api_list(api_list):
    
    object_methods, standalone_apis = separate_api_calls(api_list)
    processed_object_methods = process_object_methods(object_methods)
    processed_standalone_apis = process_standalone_apis(standalone_apis)
    api_info = combine_results(processed_object_methods, processed_standalone_apis)
    api_info = remove_unnecessary_modules(api_info)
    return api_info

if __name__ == "__main__":
    # Read the API list from the JSON file
    with open("apis.json", "r") as f:
        apis_data = json.load(f)

    result = {}
    for task_id, api_list in tqdm(list(apis_data.items())[:5]):
        result[task_id] = process_api_list(api_list)

    # Write the result to a JSON file
    with open("apis_info.json", "w") as f:
        json.dump(result, f, indent=2)
