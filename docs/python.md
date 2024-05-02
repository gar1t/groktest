# Python support

Python support is provided by the Python runtime defined in
`groktest.python`.

## Starting a runtime

Use `start_runtime` to create an initialized instance of a Python
runtime.

    >>> from groktest import start_runtime

    >>> python = start_runtime("python")

Confirm the runtime is available.

    >>> python.is_available()
    True

## Initializing a runtime for tests

The runtime can be initialized for tests using `init_for_tests` and
providing init configuration.

    >>> python.init_for_tests({"python": {"init": "msg = 'Hi!'"}})

## Executing test expressions

Create a helper to execute test expressions. We use the Python test spec
for parsing.

    >>> def run_test(s, options=None):
    ...     from groktest import parse_tests, PYTHON_SPEC
    ...     tests = parse_tests(s, PYTHON_SPEC, "<test>")
    ...     assert len(tests) == 1
    ...     result = python.exec_test_expr(tests[0], options or {})
    ...     assert result.code in (0, 1), result.code
    ...     print(result.output)
    ...     if result.short_error:
    ...         print("----short error----")
    ...         print(result.short_error)

Various tests:

    >>> run_test(">>> None")
    ⤶

    >>> run_test("""
    ... >>> 1 + 1
    ... """)
    2
    ⤶

    >>> run_test("""
    ... >>> print('''
    ... ... Line 1
    ... ... Line 2
    ... ...
    ... ... Line 2
    ... ... ''')
    ... """)
    ⤶
    Line 1
    Line 2
    ⤶
    Line 2
    ⤶
    ⤶

The Python runtime provides `short_error` in the case of an exception.
This can be used to match as an alternative to the full output.

    >>> run_test(">>> 1 / 0")
    Traceback (most recent call last):
      File "<test>", line 1, in <module>
    ZeroDivisionError: division by zero
    ⤶
    ----short error----
    Traceback (most recent call last):
    ZeroDivisionError: division by zero
    ⤶

Options may include `pprint` to pretty print results.

    >>> run_test("""
    ... >>> {
    ... ...     "zzzzzzzzzzzzzzzzzz": 1,
    ... ...     "yyyyyyyyyyyyyyyyyy": 2,
    ... ...     "xxxxxxxxxxxxxxxxxx": 3
    ... ... }
    ... """, {"pprint": True})
    {'xxxxxxxxxxxxxxxxxx': 3,
     'yyyyyyyyyyyyyyyyyy': 2,
     'zzzzzzzzzzzzzzzzzz': 1}
    ⤶

Without `pprint`:

    >>> run_test("""
    ... >>> {
    ... ...     "zzzzzzzzzzzzzzzzzz": 1,
    ... ...     "yyyyyyyyyyyyyyyyyy": 2,
    ... ...     "xxxxxxxxxxxxxxxxxx": 3
    ... ... }
    ... """)
    {'zzzzzzzzzzzzzzzzzz': 1, 'yyyyyyyyyyyyyyyyyy': 2, 'xxxxxxxxxxxxxxxxxx': 3}
    ⤶

Note that `msg`, which we defined for the runtime using
`init_for_tests()` above, is available in globals.

    >>> run_test(">>> print(msg)")
    Hi!
    ⤶

### Special handling for assertions

The Python runtime applies special handling to assertion errors. When it
encounters an assertion error when executing a test expression, it
applies a dict of values used in the expression as an argument to the
assertion error if one has not already been provided.

    >>> run_test(">>> x = 1; assert x < 1")
    Traceback (most recent call last):
      File "<test>", line 1, in <module>
    AssertionError: {'x': 1}
    ⤶
    ----short error----
    Traceback (most recent call last):
    AssertionError: {'x': 1}
    ⤶

If the expression provides an argument for the assertion error, it's
used as specified.

    >>> run_test(">>> x = 1; assert x < 1, f'x = {x}'")
    Traceback (most recent call last):
      File "<test>", line 1, in <module>
    AssertionError: x = 1
    ⤶
    ----short error----
    Traceback (most recent call last):
    AssertionError: x = 1
    ⤶

### Special handling for comments

The Python runtime treats comments as implicit `None` values.

    >>> run_test(">>> # This is a comment")
    ⤶

## Stopping a runtime

The Python runtime should be stopped when no longer needed.

Stop the runtime.

    >>> python.stop()

Once shut down, the runtime is no longer available.

    >>> python.is_available()
    False
