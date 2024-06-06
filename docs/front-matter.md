# Front matter

Front matter is denoted by a line `---` at the start of the file
followed by a subsequent line `---`.

Front matter is matched using `groktest._FRONT_MATTER_P`.

    >>> import groktest

    >>> def match(s):
    ...     m = groktest._FRONT_MATTER_P.match(s)
    ...     if m:
    ...         if m.group(1):
    ...             print(m.group(1))
    ...         else:
    ...             print("<empty>")
    ...     else:
    ...         print("<none>")

Failed matches:

    >>> match("")
    <none>

    >>> match("---\n---")
    <none>

    >>> match("xxx\n---\n---")
    <none>

Matches:

    >>> match("\n---\n\n---")
    <empty>

    >>> match("\n---\n\n---\n")
    <empty>

    >>> match("\n\n---\n\n---")
    <empty>

    >>> match("\n---\n\n---\n")
    <empty>

    >>> match("\n---\nxxx\n---\n")
    xxx

    >>> match("\n---\n\n---\nxxx")
    <empty>

    >>> match("\n---\nxxx\n---\nyyy")
    xxx

    >>> match("\n---\nxxx\nyyy\n---\n")
    xxx
    yyy

    >>> match("""
    ... ---
    ... foo: 123
    ... bar: 456
    ... baz:
    ...   foo: 321
    ...   bar: 654
    ... ---
    ... """)
    foo: 123
    bar: 456
    baz:
      foo: 321
      bar: 654

    >>> match("""
    ... ---
    ... { "foo": 123, "bar": 456, "baz": {
    ...   "foo": 321,
    ...   "bar": 654
    ... }}
    ... ---
    ... """)
    { "foo": 123, "bar": 456, "baz": {
      "foo": 321,
      "bar": 654
    }}

The function `parse_front_matter` parses front matter specified in a
string.

    >>> def front_matter(s: str):
    ...     return groktest.parse_front_matter(s, "<test>")

Missing front matter:

    >>> front_matter("")
    {'__src__': '<test>'}

    >>> front_matter("Nothing to see here")
    {'__src__': '<test>'}

Groktest does not consider Markdown "comments" as 'empty lines'.

    >>> front_matter("""
    ... <!-- This is a valid comment in Markdown -->
    ... ---
    ... foo: 123 # Not parsed as Groktest front matter
    ... ---
    ... """)
    {'__src__': '<test>'}

YAML:

    >>> front_matter("""
    ... ---
    ... foo: 123
    ... bar: hello
    ... ---
    ... """)  # +pprint
    {'__src__': '<test>', 'bar': 'hello', 'foo': 123}

JSON:

    >>> front_matter("""
    ... ---
    ... {
    ...   "foo": 123,
    ...   "bar": "hello"
    ... }
    ... ---
    ... """)  # +pprint
    {'__src__': '<test>', 'bar': 'hello', 'foo': 123}

TOML:

    >>> front_matter("""
    ... ---
    ... foo = 123
    ... bar = "hello"
    ... ---
    ... """)  # +pprint
    {'__src__': '<test>', 'bar': 'hello', 'foo': 123}

Front matter must be mapping (dict).

    >>> front_matter("""
    ... ---
    ... 123
    ... ---
    ... """)  # +stderr
    Invalid front matter in <test>, expected mapping but got int
    {'__src__': '<test>'}

Groktest falls back on YAML, which parses invalid JSON and TOML as
strings. In such cases, the error message is modified to call attention
to a possible formatting/syntax error.

    >>> front_matter("""
    ... ---
    ... foo = bar
    ... ---
    ... """)  # +stderr
    Unable to parse front matter in <test> - verify valid JSON, TOML, or YAML
    {'__src__': '<test>'}

    >>> front_matter("""
    ... ---
    ... { "foo": "bar }
    ... ---
    ... """)  # +stderr
    Unable to parse front matter in <test> - verify valid JSON, TOML, or YAML
    {'__src__': '<test>'}

## YAML

Groktest supports YAML front matter using `groktest._vendor_strictyaml`.

The internal function `_parse_yaml` implements support for parsing
simplified YAML.

    >>> def parse_yaml(s):
    ...     return groktest._parse_yaml(s, "<test>")

    >>> parse_yaml("""
    ... i: 123
    ... f: 1.123
    ... s1: hello
    ... s2: 'a quoted value'
    ... s3: "another quoted value"
    ... b1: true
    ... b2: yes
    ... b3: false
    ... b4: no
    ... """)  # +pprint
    {'b1': True,
     'b2': True,
     'b3': False,
     'b4': False,
     'f': 1.123,
     'i': 123,
     's1': 'hello',
     's2': 'a quoted value',
     's3': 'another quoted value'}

    >>> parse_yaml("""
    ... s1: [1, 2, 3]
    ... s2: {foo: 123, bar: 456}
    ... """)  # +pprint
    {'s1': [1, 2, 3], 's2': {'bar': 456, 'foo': 123}}

    >>> parse_yaml("""
    ... # This is a comment
    ... foo: 123
    ... """)
    {'foo': 123}

    >>> parse_yaml("""
    ... foo: 123  # this is not a comment
    ... """)
    {'foo': 123}

    >>> parse_yaml("""
    ... test-options: +match -case
    ... """)
    {'test-options': '+match -case'}

## JSON

JSON may be used in front matter to define full format configuration.
The internal `_try_parse_json` implements support for parsing JSON
front matter.

    >>> def parse_json(s):
    ...     return groktest._parse_json(s, "<test>")

    >>> parse_json("1")
    1

    >>> parse_json("{}")
    {}

    >>> parse_json("not valid JSON")
    Traceback (most recent call last):
    ValueError: Expecting value: line 1 column 1 (char 0)

    >>> parse_json("""
    ... {
    ...   "test-config": {
    ...     "ps1": ">",
    ...     "ps2": "+",
    ...     "parse-types": {
    ...       "id": "[a-f0-9]{8}"
    ...     }
    ...   }
    ... }
    ... """) # +json
    {
      "test-config": {
        "parse-types": {
          "id": "[a-f0-9]{8}"
        },
        "ps1": ">",
        "ps2": "+"
      }
    }

## TOML

TOML based config is supported using `groktest._vendor_tomli`.

    >>> def parse_toml(s):
    ...     return groktest._parse_toml(s, "<test>")

    >>> parse_toml("""
    ... test-type = "doctest"
    ... """)
    {'test-type': 'doctest'}

    >>> parse_toml("""
    ... [test-config]
    ... ps1 = ">"
    ... ps2 = "+"
    ...
    ... [test-config.parse-types]
    ... id = "[a-f0-9]{8}"
    ... """)  # +pprint
    {'test-config': {'parse-types': {'id': '[a-f0-9]{8}'},
                     'ps1': '>',
                     'ps2': '+'}}

## Top-level front matter to config

Groktest config is a normalized structure used internally. Front matter
may be specified using Groktest config or it may use a simplified
top-level schema.

The mapping of simplified front matter to config is described by
`groktest.FRONT_MATTER_TO_CONFIG`,

    >>> from groktest import FRONT_MATTER_TO_CONFIG

    >>> FRONT_MATTER_TO_CONFIG  # +pprint
    {'nushell-init': ['nushell', 'init'],
     'option-functions': ['option', 'functions'],
     'parse-functions': ['parse', 'functions'],
     'parse-types': ['parse', 'types'],
     'python-init': ['python', 'init'],
     'test-options': ['options']}

Front matter is converted to config using `front_matter_to_config`.

    >>> from groktest import front_matter_to_config

In the simple case, fully defined configuration is passed through.

    >>> front_matter_to_config({
    ...     "tool": {
    ...         "groktest": {
    ...             "foo": "anything here is passed through",
    ...             "bar": 123
    ...         }
    ...     }
    ... })
    {'foo': 'anything here is passed through', 'bar': 123}

For simplified top-level config, as specified in
`FRONT_MATTER_TO_CONFIG`, values are applied to the canonical config
structure.

    >>> front_matter_to_config({
    ...     "test-options": {"pprint": True},
    ...     "python-init": "import foobar"
    ... })
    {'options': {'pprint': True}, 'python': {'init': 'import foobar'}}
