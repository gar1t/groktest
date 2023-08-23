---
test-options: +wildcard
python-init: "msg = 'Hello!'"
---

# Python Globals

    >>> pprint(sorted(globals()))
    ['__builtins__',
     '__file__',
     '__name__',
     'load_project_config',
     'msg',
     'path',
     'pprint',
     're']

Python tests have access to the standard set of Python builtins.

    >>> sorted(__builtins__)
    ['ArithmeticError', 'AssertionError', {}, 'zip']

`__name__` is the test file base name.

    >>> __name__
    'python-globals.md'

`__file__` is the full path to the test file.

    >>> __file__  # +paths
    '{}/examples/python-globals.md'

`pprint` is provided by the Python runtime to print formatted values.
This provides for consistent value display that wraps appropriately in
test docs.

    >>> pprint(list(range(0, 1000000, 100000)))
    [0,
     100000,
     200000,
     300000,
     400000,
     500000,
     600000,
     700000,
     800000,
     900000]

All other globals are configured by `python-init` configuration, which
may be defined in project configuration (i.e. `pyproject.toml`) and in
test front matter. In this case, Python globals are initialized by
`python-init` defined in both project config and in the front matter
above.

Show project config using `load_project_config`:

    >>> project_config = path.normpath(__file__ + "/../../pyproject.toml")

    >>> pprint(load_project_config(project_config))
    {'__src__': '{}/pyproject.toml',
     'exclude': ['docs/yaml.md', 'examples/unknown-format.md'],
     'include': ['README.md', 'docs/*.md', 'examples/*.md'],
     'python-init': 'from groktest import load_project_config\n'
                    'from os import path\n'
                    'import re\n'}


    >>> {"foo": 123}
    {'foo': {foo:d}}

    >>> foo
    123

`re` is available via project config:

    >>> re.match(r"Hello (.+)", "Hello Cat")
    <re.Match object; span=(0, 9), match='Hello Cat'>

`msg` is defined in front matter above:

    >>> print(msg)
    Hello!


    >> load_project_config()
