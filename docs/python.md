---
test-type: doctest
---

# Python support

Python support is provided by the Python runtime defined in
`groktest.python`.

We can instanitate a Python runtime directly or by using
`groktest.init_runtime`. In either case we need configuration.

    >>> from groktest import PYTHON_CONFIG

Use `init_runtime` to create an initialized instance of a Python
runtime.

    >>> from groktest import init_runtime

    >>> python = init_runtime(PYTHON_CONFIG)

Confirm the runtime is available.

    >>> python.is_available()
    True

Create a helper to execute test expressions.

    >>> def run_test(s):
    ...     from groktest import parse_tests
    ...     tests = parse_tests(s, PYTHON_CONFIG, "<test>")
    ...     assert len(tests) == 1
    ...     result = python.exec_test_expr(tests[0])
    ...     assert result.code in (0, 1), (result.code, result.output)
    ...     print(result.output)

Various tests:

    >>> run_test("""
    ... >>> 1 + 1
    ... """)
    2

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

    >>> run_test(">>> 1 / 0")  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    ZeroDivisionError: division by zero

Shut down the runtime.

    >>> python.shutdown()

Once shut down, the runtime is no longer available.

    >>> python.is_available()
    False
