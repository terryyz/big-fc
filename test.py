import re
import json

def parse_api_info(api_info):
    if api_info['type'] == 'constant':
        return create_constant_schema(api_info)
    elif 'signature' in api_info and api_info['signature']:
        return create_parameter_schema(parse_signature(api_info['signature']))
    else:
        return None

def create_constant_schema(api_info):
    schema = {
        "type": "constant",
    }
    
    # value = api_info.get('value')
    # if value is not None:
    #     try:
    #         # Try to parse the value as an integer or float
    #         parsed_value = int(value)
    #     except ValueError:
    #         try:
    #             parsed_value = float(value)
    #         except ValueError:
    #             # If it's not a number, treat it as a string
    #             parsed_value = value.strip("'\"")
        
    #     schema["properties"]["value"]["const"] = parsed_value
    #     schema["properties"]["value"]["type"] = type(parsed_value).__name__
    
    return schema

def parse_signature(signature):
    # Remove the outer parentheses
    print(signature)
    signature = signature.strip('()')
    
    # Split the signature into individual parameters
    params = re.split(r',\s*(?![^[]*\])', signature)
    
    parameters = {}
    for param in params:
        # Split each parameter into name, type annotation, and default value
        parts = param.split('=', 1)
        name_and_type = parts[0].strip()
        
        if ':' in name_and_type:
            name, type_annotation = name_and_type.split(':', 1)
            name = name.strip()
            type_annotation = type_annotation.strip().strip("'")
        else:
            name = name_and_type
            type_annotation = None
        
        if name.startswith('*') or name == '' or name == 'self':
            # Handle *args and **kwargs
            continue
        
        param_info = {}
        
        if type_annotation:
            param_info["type"] = parse_type_annotation(type_annotation)
        
        if len(parts) > 1:
            # There's a default value
            default = parts[1].strip()
            parsed_default = parse_default_value(default)
            param_info["default"] = parsed_default
            # Infer type from default value if not explicitly specified
            if "type" not in param_info or param_info["type"] == ["object"]:
                param_info["type"] = [type(parsed_default).__name__]
        # else:
        #     # No default value, assume it's an object
        #     param_info["type"] = ["object"]
        
        # Handle default value
        # if len(parts) > 2:
        #     default = parts[2].strip()
        #     parsed_default = parse_default_value(default)
        #     param_info["default"] = parsed_default
            
        #     # Infer type from default value if not explicitly specified
        #     if "type" not in param_info or param_info["type"] == ["object"]:
        #         param_info["type"] = [type(parsed_default).__name__]
        
        parameters[name] = param_info
    return parameters

def parse_type_annotation(annotation):
    if '|' in annotation:
        types = [t.strip().lower() for t in annotation.split('|')]
        parsed_types = set()
        for t in types:
            if t == 'none':
                parsed_types.add('null')
            elif t.startswith('os.pathlike'):
                parsed_types.add('string')
            else:
                parsed_types.add(t)
        return list(parsed_types)
    elif annotation.lower().startswith('os.pathlike'):
        return ['string']
    else:
        print(annotation)
        return [annotation.lower()]

def parse_default_value(default):
    if default.lower() == 'none':
        return None
    elif default in ('True', 'False'):
        return default == 'True'
    elif default.startswith("'") or default.startswith('"'):
        return default.strip("'\"")
    elif default.replace('-', '').isdigit():  # Allow negative integers
        return int(default)
    elif default.replace('.', '').replace('-', '').isdigit():  # Allow negative floats
        return float(default)
    else:
        return default

def create_parameter_schema(parsed_signature):
    schema = {
        "type": "object",
        "properties": {}
    }
    
    for param_name, param_info in parsed_signature.items():
        param_schema = {}
        if "type" in param_info:
            types = param_info["type"]
            if isinstance(types, list):
                cleaned_types = []
                for t in types:
                    if t == "none":
                        cleaned_types.append("null")
                    elif t in ["true", "false"]:
                        cleaned_types.append("boolean")
                    elif t == "int":
                        cleaned_types.append("integer")
                    else:
                        cleaned_types.append(t)
                param_schema["type"] = cleaned_types if len(cleaned_types) > 1 else cleaned_types[0]
            else:
                if types == "none":
                    param_schema["type"] = "null"
                elif types in ["true", "false"]:
                    param_schema["type"] = "boolean"
                elif types == "int":
                    param_schema["type"] = "integer"
                else:
                    param_schema["type"] = types
        
        # if "default" in param_info:
        #     default = param_info["default"]
            # if default == "True":
            #     param_schema["default"] = True
            # elif default == "False":
            #     param_schema["default"] = False
            # elif default == "None":
            #     param_schema["default"] = None
            # else:
            #     param_schema["default"] = default
        
        # if param_schema:  # Only add non-empty parameter schemas
        schema["properties"][param_name] = param_schema
    return schema

def process_api_info(api_info):
    """Process the API info JSON and convert signatures to parameter schemas."""
    for api_name, api_data in api_info.items():
        if 'type' not in api_data:
            continue
        schema = parse_api_info(api_data)
        if schema:
            api_data['schema'] = schema
        
        if 'chains' in api_data:
            for chain_name, chain_data in api_data['chains'].items():
                chain_schema = parse_api_info(chain_data)
                if chain_schema:
                    chain_data['schema'] = chain_schema

def main():
    # Read the JSON file
    with open('apis_info.json', 'r') as f:
        full_api_info = json.load(f)
    
    # Process the API info for BigCodeBench/82
    process_api_info(full_api_info["BigCodeBench/15"])
    print(json.dumps(full_api_info["BigCodeBench/15"], indent=2))
if __name__ == "__main__":
    main()
    # Test the function
    # signature = "import_name: 'str', static_url_path: 'str | None' = None, static_folder: 'str | os.PathLike[str] | None' = 'static', static_host: 'str | None' = None, host_matching: 'bool' = False, subdomain_matching: 'bool' = False, template_folder: 'str | os.PathLike[str] | None' = 'templates', instance_path: 'str | None' = None, instance_relative_config: 'bool' = False, root_path: 'str | None' = None"

    # parsed = parse_signature(signature)
    # print(signature)
    # print(parsed)
    # print("---")