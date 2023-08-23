---
[tool.groktest]
type = "doctest"
options = "+ELLIPSIS"
---

# Python support

Python support is provided by the Python runtime defined in
`groktest.python`.

Use `init_runtime` to create an initialized instance of a Python
runtime.

    >>> from groktest import init_runtime

    >>> python = init_runtime("python")

Confirm the runtime is available.

    >>> python.is_available()
    True

Create a helper to execute test expressions. We use the Python test spec
for parsing.

    >>> def run_test(s):
    ...     from groktest import parse_tests, PYTHON_SPEC
    ...     tests = parse_tests(s, PYTHON_SPEC, "<test>")
    ...     assert len(tests) == 1
    ...     result = python.exec_test_expr(tests[0])
    ...     assert result.code in (0, 1), (result.code, result.output)
    ...     print(result.output)

Various tests:

    >>> run_test(">>> None")
    <BLANKLINE>

    >>> run_test("""
    ... >>> 1 + 1
    ... """)
    2
    <BLANKLINE>

    >>> run_test("""
    ... >>> print('''
    ... ... Line 1
    ... ... Line 2
    ... ...
    ... ... Line 2
    ... ... ''')
    ... """)
    <BLANKLINE>
    Line 1
    Line 2
    <BLANKLINE>
    Line 2
    <BLANKLINE>
    <BLANKLINE>

    >>> run_test(">>> 1 / 0")
    Traceback (most recent call last):
      ...
      File "<test>", line 1, in <module>
    ZeroDivisionError: division by zero
    <BLANKLINE>

Stop the runtime.

    >>> python.shutdown()

Once shut down, the runtime is no longer available.

    >>> python.is_available()
    False
