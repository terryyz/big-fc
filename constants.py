FEW_SHOT_EXAMPLES="""\
# Hierarchical API call:
numpy.linalg.inv(a)

# Independent API call:
inverse_matrix(matrix)
"""

POSITIVE_TEMPLATE="""\
Creatively propose a self-contained and non-hierarchical API call to replace the following hierarchical API call.

- The name of the proposed API call **must not contain any dots** and refers to the high-level functionality.
- The name format of the proposed API call can be either **snake_case** or **camelCase**.
- The signature of the proposed API call should be the almost same as the given hierarchical API call, but the names of positional arguments can be different.
- The proposed proposed API call should be as natural as possible, paired with a short description similar to the given hierarchical API call.
- The return type of the proposed API call **must be the same** as the given hierarchical API call.
- The "type" of proposed API call **must be the same** as the given hierarchical API call.

# Hierarchical API call in JSON:
```json
{api}
```

# Example of how the hierarchical API call is used in the code:
```python
{example}
```
"""

NEGATIVE_TEMPLATE="""\
Creatively provide a self-contained independent API call and non-hierarchical API call, in contrast to the given hierarchical API call.

- The name of the proposed API call **must not contain any dots** and refers to the high-level functionality.
- The name format of the proposed API call can be either **snake_case** or **camelCase**.
- The functionality and return type of the proposed API call must be **very different** from any API calls in the code.

# Hierarchical API call in JSON:
```json
{api}
```

# Proposed API call should not be applied to the following code:
```python
{example}
```
"""

RESPONSE_TEMPLATE="""\
# Proposed API call in JSON (name in **snake_case** or **camelCase**) {{"name": "", "type": {type}, "signature": "", "return_type": "", "short_description": ""}}:
```json
{_MAGIC_SPLITTER_}
```
"""