# Test parsing

Test parsing is implemented with the help of regular expressions, which
must be provided as test configuration.

Groktest uses regular expressions for the following:

- Test definition: a test expression and corresponding expected result
- Test options: comment-based configuration per test
- Error messages (TODO is this true??)

Test definitions must use three named capture groups:

- `expr`
- `indent`
- `expected`

`expr` captures the test expression, which may span multiple lines.
Typically a test expression scheme uses PS1 and PS2 prompt strings to
denote the first line and subsequent lines respectively.

`indent` captures the sequence of space chars (` `) that offsets the
first test line. Subsequent test lines must use the same indent level.

`expected` captures the expected result of the test.

Groktest applies common test parsing behavior across all supported
tests.

## Default configuration

Default configuration is provided by `groktest.DEFAULT_SPEC`.

### Test pattern

Tests are captured using the configured `test_pattern` regular
expression. The default pattern uses PS1 and PS2 prompts to denote the
test expression. It captures the subsequent block of non-empty lines as
the test expected output.

Groktest's default pattern uses the `doctest` prompts.

    >>> from groktest import DEFAULT_SPEC

    >>> DEFAULT_SPEC.ps1
    '>>>'

    >>> DEFAULT_SPEC.ps2
    '...'

    >>> (1 +
    ... 1)
    2

Function to print found tests using the default configuration:

    >>> def find_tests(s):
    ...     from pprint import pprint
    ...     for m in DEFAULT_SPEC.test_pattern.finditer(s):
    ...         pprint(m.groupdict())

Single line test expression, no expected output, no indent:

    >>> find_tests(">>> None")
    {'expected': '', 'expr': '>>> None', 'indent': ''}

Single line test expression, single line expected result, no indent:

    >>> find_tests(">>> 1\n1")
    {'expected': '1', 'expr': '>>> 1', 'indent': ''}

Same test with two-space indent:

    >>> find_tests("  >>> 1\n1")
    {'expected': '1', 'expr': '  >>> 1', 'indent': '  '}

Multi-line expression and expected:

    >>> find_tests("""
    ...   >>> print('''1
    ...   ... 2''')
    ...   1
    ...   2
    ... """)
    {'expected': '  1\n  2\n',
     'expr': "  >>> print('''1\n  ... 2''')",
     'indent': '  '}

### Test objects

Groktest applied `test_pattern` as outlined above to generate a
`groktest.Test` instance that Groktest can evaluate.

Function to parse string input and print parsed tests.

    >>> def parse_tests(s):
    ...     import groktest
    ...
    ...     for i, test in enumerate(groktest.parse_tests(
    ...         s, DEFAULT_SPEC, "<test>"
    ...     )):
    ...         if i > 0:
    ...             print("---")
    ...         print(f"line {test.line} in {test.filename}")
    ...         print(f"expr: {test.expr!r}")
    ...         print(f"expected: {test.expected!r}")

One line expression, nothing expected:

    >>> parse_tests(">>> None")
    line 1 in <test>
    expr: 'None'
    expected: ''

One line expression, one line of expected output:

    >>> parse_tests(">>> 1\n1")
    line 1 in <test>
    expr: '1'
    expected: '1'

Multi-line expression, multiple lines of output:

    >>> parse_tests("""
    ...   >>> print('''1
    ...   ... 2''')
    ...   1
    ...   2
    ... """)
    line 2 in <test>
    expr: "print('''1\n2''')"
    expected: '1\n2'

Multi-test example:

    >>> parse_tests("""
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

    >>> parse_tests("""
    ...   >>> 1
    ...  1
    ... """)  # +wildcard
    Traceback (most recent call last):
    ...
    ValueError: File "<test>", line 2, in test: inconsistent leading whitespace

Prompts must be followed by at least one space char.

    >>> parse_tests("""
    ...   >>>1
    ...   1
    ... """)  # +wildcard
    Traceback (most recent call last):
    ...
    ValueError: File "<test>", line 2, in test: space missing after prompt

    >>> parse_tests("""
    ...   >>> print(
    ...   ..."hello")
    ... """)  # +wildcard
    Traceback (most recent call last):
    ...
    ValueError: File "<test>", line 3, in test: space missing after prompt
