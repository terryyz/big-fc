FEW_SHOT_EXAMPLES="""\
# Hierarchical API call:
numpy.linalg.inv(a)

# Independent API call:
inverse_matrix(matrix)
"""

POSITIVE_TEMPLATE="""\
Creatively propose an API schema to rephrase the given hierarchical API schema.

- "name" of the proposed API **must not contain any dots** and refers to the high-level functionality.
- "name" of the proposed API can be either **snake_case** or **camelCase**.
- "type" of the proposed API **must align** with the "type" of the given API, unless the "type" of the given API is not given.
- "signature" of the proposed API **must align** with the "signature" of the given API, though the parameter names can be different.
- "description" of the proposed API **must be concise** and **align** with the given API functionality.

# Given API schema:
```json
{api}
```
"""

NEGATIVE_TEMPLATE="""\
Creatively provide a self-contained API call, **in contrast to** the given hierarchical API call.

- The name of the proposed API **must not contain any dots** and refers to the high-level functionality.
- The name format of the proposed API can be either **snake_case** or **camelCase**.
- The functionality and "type" of the proposed API must be **very different** from any API calls in the code.

# Given hierarchical API call:
```json
{api}
```

# Proposed API **must not be applicable** to the following code example:
```python
{example}
```
"""

SCHEMA = """\
# You are required to return a valid JSON object in the following schema:
```json
{
    "name": "", # The name of the API
    "type": "", # The type of the API, choose from "function", "class", "method"
    "signature": "(...)", # A concise signature of the API, wrapped with parentheses
    "description": "", # A concise description of the API
    "parameters": { # If the API is callable, it has parameters
        "type": "object", # The type of the parameters
        "properties": { # The properties of the parameters
            PARAM_1: {
                "type": "",
                "default": ""
            },
            ...
        }
    }
}
```
"""

OBJECT_SCHEMA = """\
# You are required to return a valid JSON object in the following schema:
```json
{
    API: {
        "name": "", # The name of the API
        "type": "", # The type of the API, choose from "function", "class", "method"
        "signature": "", # A concise signature of the API, wrapped with parentheses
        "description": "", # A concise description of the API
        "parameters": { # If the API is callable, it has parameters
            "type": "object", # The type of the parameters
            "properties": { # The properties of the parameters
                PARAM_1: {
                    "type": "",
                    "default": ""
                },
                ...
            }
        }
    }
}
```
"""

RESPONSE_TEMPLATE="""\
# Proposed API schema:
```json
{_MAGIC_SPLITTER_}
```
"""