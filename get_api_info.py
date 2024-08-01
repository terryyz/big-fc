import inspect
import importlib
import sys

def get_api_info(api):
    try:
        # Remove newline character if present
        api = api.strip()
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
        apis = list(set([l.split("(")[0] for l in f.readlines()]))

    with open("apis_info.jsonl", "w") as f:
        for api in tqdm(apis[:]):
            api_info = get_api_info(api)
            f.write(json.dumps(api_info) + "\n")
