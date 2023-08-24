---
test-options = "+parse"
parse-functions = "custom_types"
---

# Custom parse types

Parse types can be implemented as Python functions. To make custom parse
types functions available in tests, use `parse-type-functions` and refer
to a Python module. The module may be relative to the test file or
available in the Python system path. In this case, the module file is
[alongside this test document](custom_types.py).

[`custom_types.py`](custom_types.py) exports two custom parse types:
`ver` and `loud`.

`ver` matches a simpler version number.

    >>> 'Release version 0.1.0'
    'Release version {}'

When bound to a variable, the variable is a tuple of the three version
parts as ints.

    >>> 'Release version 0.10.1'
    'Release version {release_ver:ver}'

    >>> release_ver
    [0, 10, 1]

`loud` convers the matched string to upper-case.

    >>> "They said 'the world is flat'"
    "They said '{what_they_said:loud}'"

    >>> what_they_said
    'THE WORLD IS FLAT'

Note that the function that implements `loud` is named `parse_upper`.
This function is registered as `loud` by setting its `type_name`
attribute.

Note that `parse_internal` is defined in
[`custom_types.py`](custom_types.py). However, it's not available as a
parse type because it's not listed in the module's `__all__` attribute.

    >>> 123  # +fails
    {:internal}
