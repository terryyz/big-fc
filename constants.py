FEW_SHOT_EXAMPLES="""\
# Hierarchical API call:
numpy.linalg.inv(a)

# Independent API call:
inverse_matrix(matrix)
"""

POSITIVE_TEMPLATE="""\
Creatively propose a self-contained API to replace the following hierarchical API call.

- The name of the proposed API **must not contain any dots** and refers to the high-level functionality.
- The name format of the proposed API can be either **snake_case** or **camelCase**.
- The proposed proposed API should be as natural as possible, paired with a short description similar to the given hierarchical API call.
- The "type" of the proposed API **must be the same** as the given hierarchical API call.
- The signature of the proposed API **must be aligned** with how the hierarchical API is invoked.

# Given hierarchical API call:
```json
{api}
```

# Hierarchical API documentation:
```json
{api_doc}
```

# Code example:
```python
{example}
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

RESPONSE_TEMPLATE="""\
# Proposed API in the perfect JSON (name in **snake_case** or **camelCase**) {{"label": "{label}", "name": "", "type": "{type}", "signature": "",  "short_description": ""}}:
```json
{_MAGIC_SPLITTER_}
```
"""