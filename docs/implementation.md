---
test-type: doctest
---

# Groktest Implementation

## Customizer API

A _customizer_ is someone who customizes Groktest to provide new or
modified behavior.

- Languages
- Pattern match schemes
- Pattern features

TODO

## Internal API

The tests in this section demonstrate internal Groktest behavior. These
may be considered unit tests.

    >>> import groktest

### Parsing front matter

Front matter is denoted by a line `---` at the start of the file
followed by a subseuqnet line `---`.

Front matter is matched using `groktest._FRONT_MATTER_P`.

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
    {}

    >>> fm("Nothing to see here")
    {}

Groktest does not consider Markdown "comments" as 'empty lines'.

    >>> fm("""
    ... <!-- This is a valid comment in Markdown -->
    ... ---
    ... foo: 123 # Not parsed as Groktest front matter
    ... ---
    ... """)
    {}

Simple YAML:

    >>> fm("""
    ... ---
    ... foo: 123
    ... bar: hello
    ... ---
    ... """)
    {'bar': 'hello', 'foo': 123}

JSON:

    >>> fm("""
    ... ---
    ... {
    ...   "foo": 123,
    ...   "bar": "hello"
    ... }
    ... ---
    ... """)
    {'bar': 'hello', 'foo': 123}

INI:

    >>> fm("""
    ... ---
    ... foo = 123
    ... bar = hello
    ... ---
    ... """)
    {'bar': 'hello', 'foo': 123}

The sections below provide detailed examples of front-matter formats.

#### Simple YAML

Groktest supports simple YAML front matter without dependencies on
PyYAML. For full YAML support, PyYAML must be installed. See
[yaml-support.md](yaml-support.md) for details on parsing full YAML.

For the tests below we use `_try_parse_simple_yaml` to explicit parse
using the PyYAML independent routine.

    >>> def parse_simple_yaml(s):
    ...     pprint(groktest._try_parse_simple_yaml(s, "<test>", raise_error=True))

    >>> parse_simple_yaml("""
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

    >>> parse_simple_yaml("""
    ... s1: [1, 2, 3]
    ... s2: {foo: 123, bar: 456}
    ... """)
    {'s1': '[1, 2, 3]', 's2': '{foo: 123, bar: 456}'}

In the simple YAML support, comments can only appear on separate lines.

    >>> parse_simple_yaml("""
    ... # This is a comment
    ... foo: 123
    ... """)
    {'foo': 123}

    >>> parse_simple_yaml("""
    ... foo: 123  # this is not a comment
    ... """)
    {'foo': '123  # this is not a comment'}

#### JSON

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
    ...     "ps1": "> ",
    ...     "parse-types": {
    ...       "id": "[a-f0-9]{8}"
    ...     }
    ...   }
    ... }
    ... """)
    {'test-config': {'parse-types': {'id': '[a-f0-9]{8}'}, 'ps1': '> '}}

#### INI

INI based config supported using the `configparser` module.

    >>> def parse_ini(s):
    ...     pprint(groktest._try_parse_ini(s, "<test>", raise_error=True))

    >>> parse_ini("""
    ... [test-config]
    ... ps1: '> '
    ...
    ... [test-config.parse-types]
    ... id: [a-f0-9]{8}
    ... """)
    {'test-config': {'ps1': '> '}, 'test-config.parse-types': {'id': '[a-f0-9]{8}'}}

Indented sections are not supported.

    >>> parse_ini("""
    ... [foo]
    ...   [bar]
    ...   baz: 123
    ... """)
    {'bar': {'baz': 123}, 'foo': {}}

#### TOML

This section should self-destruct if not modified in 24 months.

TOML is supported insofar as it complies with the INI convention. E.g.
intended sections are not supported (see below).

Proper TOML support may be added if desired using a TOML parser.
However, this support must be made optional, as with full YAML support,
to avoid a dependency on an external library.

Note that TOML support is slated for Python 3.11. This could be one way
to avoid a dependency on another library, however, it would incur a
dependency on Python 3.11.

It's not clear that TOML support is needed.

### Parsing tests

Test parsing is implemented with the help of regular expressions, which
must be provided as test configuration.

Groktest required regular expressions for the following:

- Test definition (a test expression and corresponding expected result)
- Test options (comment based configuration per test)
- Error messages

Test definitions must use three named capture groups:

- `expr`
- `indent`
- `expected`

`testexpr` captures the test expression, which may span multiple lines.
Typically a test expression scheme makes use of PS1 and PS2 prompt
strings to denote the first line and subsequent lines respective.

`indent` captures the sequence of space chars (` `) used to offset the
first line of the test. All subsequent lines associated with the test
are required to use the same indent level.

`expected` captures the expected result of the test.

#### Common parsing behavior

Groktest applies common test parsing behavior across all supported
tests.

Tests must be indented as a block using the first line indent.

#### Python

Default support for Python tests follows `doctest` in syntax.

##### Test pattern matching

    >>> def py_tests_m(s):
    ...     for m in groktest.PYTHON_CONFIG.test_pattern.finditer(s):
    ...         pprint(m.groupdict())

Single line test expression, no expexted output, no indent:

    >>> py_tests_m(">>> None")
    {'expected': '', 'expr': '>>> None', 'indent': ''}

Single line test expression, single line expected result, no indent:

    >>> py_tests_m(">>> 1\n1")
    {'expected': '1', 'expr': '>>> 1', 'indent': ''}

Same test with two-space indent:

    >>> py_tests_m("  >>> 1\n1")
    {'expected': '1', 'expr': '  >>> 1', 'indent': '  '}

Multi-line expression and expected:

    >>> py_tests_m("""
    ...   >>> print('''1
    ...   ... 2''')
    ...   1
    ...   2
    ... """)
    {'expected': '  1\n  2\n',
     'expr': "  >>> print('''1\n  ... 2''')",
     'indent': '  '}

##### Test parsing

    >>> def py_tests(s):
    ...     for i, test in enumerate(groktest.parse_tests(
    ...         s, groktest.PYTHON_CONFIG, "<test>"
    ...     )):
    ...         if i > 0:
    ...             print("---")
    ...         print(f"line {test.source.line} in {test.source.filename}")
    ...         print(f"expr: {test.expr!r}")
    ...         print(f"expected: {test.expected!r}")

One line expression, nothing expected:

    >>> py_tests(">>> None")
    line 1 in <test>
    expr: 'None'
    expected: ''

One line expression, one line of expected output:

    >>> py_tests(">>> 1\n1")
    line 1 in <test>
    expr: '1'
    expected: '1'

Multi-line expression, multiple lines of outout:

    >>> py_tests("""
    ...   >>> print('''1
    ...   ... 2''')
    ...   1
    ...   2
    ... """)
    line 2 in <test>
    expr: "print('''1\n2''')"
    expected: '1\n2'

Multi-test example:

    >>> py_tests("""
    ... Some addition:
    ...
    ...     >>> 1 + 1
    ...     2
    ...
    ... Print some lines:
    ...
    ...     >>> print(
    ...     ...     "hello\\n"
    ...     ...     "there"
    ...     ... )
    ...     hello
    ...     there
    ...
    ... And a test with no expected result:
    ...
    ...     >>> _ = os.listdir()
    ... """)
    line 4 in <test>
    expr: '1 + 1'
    expected: '2'
    ---
    line 9 in <test>
    expr: 'print(\n    "hello\\n"\n    "there"\n)'
    expected: 'hello\nthere'
    ---
    line 18 in <test>
    expr: '_ = os.listdir()'
    expected: ''

Lines following the first line of a test must be indented at least as
much.

    >>> py_tests("""
    ...   >>> 1
    ...  1
    ... """)
    Traceback (most recent call last):
    ValueError: File "<test>", line 2, in test: inconsistent leading
    whitespace

Prompts must be followed by at least one space char.

    >>> py_tests("""
    ...   >>>1
    ...   1
    ... """)
    Traceback (most recent call last):
    ValueError: File "<test>", line 2, in test: space missing after
    prompt

    >>> py_tests("""
    ...   >>> print(
    ...   ..."hello")
    ... """)
    Traceback (most recent call last):
    ValueError: File "<test>", line 3, in test: space missing after
    prompt

### Comparing test output to expected

The Groktest function `match_test_output()` is used to compare test
output (a string generated by evaluating a test expression) to the
expected output.

    >>> from groktest import match_test_output

Create a function that prints bound variables for a match.

    >>> def match(expected, test_output, types=None, case_sensitive=False):
    ...     m = match_test_output(expected, test_output, types, case_sensitive)
    ...     if m:
    ...         pprint(m.bound_variables)
    ...     else:
    ...         print("<no match>")

Match simple output.

    >>> match("1", "1")
    {}

Use format expressions.

    >>> match("{}", "1")
    {}

    >>> match("{:d}", "1")
    {}

    >>> match("{:D}", "1")
    <no match>

    >>> match("A {} cat", "A blue cat")
    {}

    >>> match("A {} cat", "A red cat")
    {}

    >>> match("A {} cat", "A red dog")
    <no match>

    >>> match("A {} cat", "A blue and red cat")
    {}

    >>> match("A {:w} cat", "A blue and red cat")
    <no match>

Use variables.

    >>> match("{x:d}", "1")
    {'x': 1}

    >>> match("A {desc} cat", "A blue cat")
    {'desc': 'blue'}

    >>> match("A {desc} cat", "A blue and red cat")
    {'desc': 'blue and red'}

Groktest match support can be customized with custom match types.

    >>> match(
    ...     "A {:color} cat",
    ...     "A blue cat",
    ...     {"color": "blue|red"}
    ... )
    {}

    >>> match(
    ...     "A {color:color} cat",
    ...     "A red cat",
    ...     {"color": "blue|red"}
    ... )
    {'color': 'red'}

    >>> match(
    ...     "A {:color} cat",
    ...     "A green cat",
    ...     {"color": "blue|red"}
    ... )
    <no match>

By default matches are case-insensitive.

    >>> match("Hello", "hello")
    {}

Compare with case sensitive.

    >>> match("Hello", "hello", case_sensitive=True)
    <no match>

Match types can specify a case-insensitive pattern using `(?i)`.

    >>> match(
    ...     "A {color:color} cat",
    ...     "A RED cat",
    ...     {"color": "(?i)blue|red"},
    ...     case_sensitive=True
    ... )
    {'color': 'RED'}

    >>> match(
    ...     "A {color:color} cat",
    ...     "A bluE cat",
    ...     {"color": "(?i)blue|red"},
    ...     case_sensitive=True
    ... )
    {'color': 'bluE'}

Patterns match across multipe lines.

    >>> match(
    ... """
    ... Traceback (most recent call last):
    ... {stack}
    ... ZeroDivisionError: division by zero
    ... """,
    ... """
    ... Traceback (most recent call last):
    ... File "<stdin>", line 1, in <module>
    ... File "<stdin>", line 2, in boom
    ... ZeroDivisionError: division by zero
    ... """
    ... )
    {'stack': 'File "<stdin>", line 1, in <module>\n'
              'File "<stdin>", line 2, in boom'}

Non-patterns are sensitive to line-endings.

    >>> match("a b", "a\nb")
    <no match>

    >>> match("a b", "\na b\n")
    <no match>

To match the previous example, the leading and trailing line-endings
need to be stripped.

    >>> match("a b", "\na b\n".strip())
    {

### Runner state

TODO

Runner state an internal construct Groktest uses when running tests.

    >> state = groktest.init_runner_state("examples/doctest.md")

Groktest loads the specified file and initializes runner state.

TODO

#### Errors

A file must exist.

    >>> groktest.init_runner_state("does_not_exist")
    Traceback (most recent call last):
    FileNotFoundError: [Errno 2] No such file or directory: 'does_not_exist'
