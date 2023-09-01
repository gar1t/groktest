---
test-type: doctest
---

# Front matter

Front matter is denoted by a line `---` at the start of the file
followed by a subseuqnet line `---`.

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

The function `_parse_front_matter()` parses front matter specified in a
string.

    >>> def fm(s: str):
    ...     pprint(groktest._parse_front_matter(s, "<test>"))

Missing front matter:

    >>> fm("")
    {'__src__': '<test>'}

    >>> fm("Nothing to see here")
    {'__src__': '<test>'}

Groktest does not consider Markdown "comments" as 'empty lines'.

    >>> fm("""
    ... <!-- This is a valid comment in Markdown -->
    ... ---
    ... foo: 123 # Not parsed as Groktest front matter
    ... ---
    ... """)
    {'__src__': '<test>'}

Simple YAML:

    >>> fm("""
    ... ---
    ... foo: 123
    ... bar: hello
    ... ---
    ... """)
    {'__src__': '<test>', 'bar': 'hello', 'foo': 123}

JSON:

    >>> fm("""
    ... ---
    ... {
    ...   "foo": 123,
    ...   "bar": "hello"
    ... }
    ... ---
    ... """)
    {'__src__': '<test>', 'bar': 'hello', 'foo': 123}

TOML:

    >>> fm("""
    ... ---
    ... foo = 123
    ... bar = hello
    ... ---
    ... """)
    {'__src__': '<test>', 'bar': 'hello', 'foo': 123}

## Simplified YAML

Groktest supports simplified YAML front matter so as not to rely on
external libraries such as PyYAML. PyYAML is required for full YAML
support. See [yaml.md](yaml.md) for details on parsing full YAML.

The internal function `_try_parse_simplified_yaml` implements support
for parsing simpligied YAML.

    >>> def parse_simplified_yaml(s):
    ...     pprint(groktest._try_parse_simplified_yaml(
    ...         s, "<test>", raise_error=True))

    >>> parse_simplified_yaml("""
    ... i: 123
    ... f: 1.123
    ... s1: hello
    ... s2: 'a quoted value'
    ... s3: "another quoted value"
    ... b1: true
    ... b2: yes
    ... b3: false
    ... b4: no
    ... """)
    {'b1': True,
     'b2': True,
     'b3': False,
     'b4': False,
     'f': 1.123,
     'i': 123,
     's1': 'hello',
     's2': 'a quoted value',
     's3': 'another quoted value'}

Any other types are treated as strings.

    >>> parse_simplified_yaml("""
    ... s1: [1, 2, 3]
    ... s2: {foo: 123, bar: 456}
    ... """)
    {'s1': '[1, 2, 3]', 's2': '{foo: 123, bar: 456}'}

In the simple YAML support, comments can only appear on separate lines.

    >>> parse_simplified_yaml("""
    ... # This is a comment
    ... foo: 123
    ... """)
    {'foo': 123}

    >>> parse_simplified_yaml("""
    ... foo: 123  # this is not a comment
    ... """)
    {'foo': '123  # this is not a comment'}

    >>> parse_simplified_yaml("""
    ... test-options: +match -case
    ... """)
    {'test-options': '+match -case'}

The underlying implementation uses `configparse` as an opportunistic
method to parse a single top-level map of names to values. The
implementation parses any valid Python INI, despite it not being valid
YAML.

INI sections are ignored in the result.

    >>> parse_simplified_yaml("""
    ... [my-section]
    ... foo: 123
    ... """)
    {}

Top level assignments may be made using an equals sign (`=`), which is
also not valid YAML.

    >>> parse_simplified_yaml("""
    ... foo = 123
    ...
    ... [my-section]
    ... foo = 456
    ... """)
    {'foo': 123}

## JSON

JSON may be used in front matter to define full format configuration.
The internal `_try_parse_json` implements support for parsing JSON
front matter.

    >>> def parse_json(s):
    ...     pprint(groktest._try_parse_json(s, "<test>", raise_error=True))

    >>> parse_json("1")
    1

    >>> parse_json("{}")
    {}

    >>> parse_json("not valid JSON")
    Traceback (most recent call last):
    json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)

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
    ... """)
    {'test-config': {'parse-types': {'id': '[a-f0-9]{8}'},
                     'ps1': '>',
                     'ps2': '+'}}

## TOML

TOML based config supported using `groktest._vendor_tomli`.

    >>> def parse_toml(s):
    ...     pprint(groktest._try_parse_toml(s, "<test>", raise_error=True))

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
    ... """)
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

    >>> pprint(FRONT_MATTER_TO_CONFIG)
    {'parse-functions': ['parse', 'functions'],
     'parse-types': ['parse', 'types'],
     'python-init': ['python', 'init'],
     'test-options': ['options']}

Front matter is converted to config using `front_matter_to_config`.

    >>> from groktest import front_matter_to_config  # -skiprest

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
