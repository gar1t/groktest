---
test-options: +wildcard
python-init: "msg = 'Hello!'"
---

# Python Globals

    >>> sorted(globals())  # +pprint
    ['__builtins__',
     '__file__',
     '__name__',
     'msg',
     'os',
     'pprint',
     're',
     'run']

Python tests have access to the standard set of Python builtins.

    >>> min, max, sorted  # -space
    (<built-in function min>,
     <built-in function max>,
     <built-in function sorted>)

`__name__` is the test file base name.

    >>> __name__
    'python-globals.md'

`__file__` is the full path to the test file.

    >>> __file__  # +paths
    '.../examples/python-globals.md'

All other globals are configured by `python-init` configuration, which
may be defined in project configuration (i.e. `pyproject.toml`) and in
test front matter. In this case, Python globals are initialized by
`python-init` defined in both project config and in the front matter
above.

Show project config using `load_project_config`:

    >>> project_config = os.path.normpath(__file__ + "/../../pyproject.toml")
    >>> from groktest import load_project_config

    >>> load_project_config(project_config)  # +pprint +paths +wildcard
    {'__src__': '.../pyproject.toml',
     'exclude': ['docs/yaml.md',
                 'examples/unknown-format.md',
                 'examples/failfast.md'],
     'include': ['README.md', 'docs/*.md', 'examples/*.md'],
     'python': {'init': 'from groktest._test_util import *\n'}}

`re` is available via project config:

    >>> re.match(r"Hello (.+)", "Hello Cat")
    <re.Match object; span=(0, 9), match='Hello Cat'>

`msg` is defined in front matter above:

    >>> print(msg)
    Hello!
