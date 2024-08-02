import inspect
import importlib
import sys
import ast

def filter_unused_args(signature, api_call):
    # Extract arguments from the signature
    args = [arg.strip() for arg in signature[1:-1].split(',')]
    
    # Parse the API call
    try:
        call = ast.parse(api_call).body[0].value
        if isinstance(call, ast.Call):
            used_args = set([arg.arg for arg in call.keywords])
            used_args.update([args[i].split(':')[0].split('=')[0].strip() for i in range(len(call.args))])
        else:
            return signature  # Return original if not a function call
    except:
        return signature  # Return original if parsing fails
    
    # Filter arguments while maintaining original order
    filtered_args = [arg for arg in args if arg.split(':')[0].split('=')[0].strip() in used_args]
    
    # Construct new signature
    return f"({', '.join(filtered_args)})"

# # Test case
# signature = "(data=None, index: 'Axes | None' = None, columns: 'Axes | None' = None, dtype: 'Dtype | None' = None, copy: 'bool | None' = None) -> 'None'"
# api_call = "pandas.DataFrame(data, columns=['Values'])"

# result = filter_unused_args(signature, api_call)
# print(f"Original: {signature}")
# print(f"API call: {api_call}")
# print(f"Filtered: {result}")
    

def get_api_info(api_call):
    try:
        # Remove newline character if present
        api = api_call.strip().split("(")[0]
        flg = False
        if api == "datetime.datetime.datetime":
            api = "datetime.datetime"
            flg = True
        # Split the API string into parts
        parts = api.split('.')
                
        # Import the module step by step
        module = None
        for i, part in enumerate(parts):
            if i == 0:
                module = importlib.import_module(part)
            else:
                try:
                    module = getattr(module, part)
                except AttributeError:
                    # Try importing as a submodule
                    submodule = importlib.import_module(f"{'.'.join(parts[:i+1])}")
                    module = submodule
        
        # Prepare the result dictionary
        result = {'name': "datetime.datetime.datetime"} if flg else {'name': api}
        result["call"] = api_call
        if inspect.ismodule(module):
            result['type'] = 'module'
            result['signature'] = None
        elif inspect.isclass(module):
            result['type'] = 'class'
            try:
                result['signature'] = str(inspect.signature(module))
            except ValueError:
                result['signature'] = None
        elif callable(module):
            result['type'] = 'callable'
            try:
                result['signature'] = str(inspect.signature(module))
            except ValueError:
                result['signature'] = None
        else:
            result['type'] = 'constant'
            result['value'] = str(module)
            result['signature'] = None

        if result['signature'] and "(" in api_call:
            result['signature'] = filter_unused_args(result['signature'], api_call)
        result['docstring'] = inspect.getdoc(module)
        result['short_docstring'] = (inspect.getdoc(module) or '').split('\n\n')[0]


        return result

    except ImportError as e:
        return {'name': api, 'error': f'Import error: {str(e)}'}
    except AttributeError as e:
        return {'name': api, 'error': f'Attribute error: {str(e)}'}
    except Exception as e:
        return {'name': api, 'error': str(e)}

    
if __name__ == "__main__":
    import json
    from tqdm import tqdm
    with open("apis.txt", "r") as f:
        apis = list(set(f.readlines()))[:10]

    with open("apis_info.jsonl", "w") as f:
        for api in tqdm(apis[:]):
            api_info = get_api_info(api)
            f.write(json.dumps(api_info) + "\n")
