---
[tool.groktest]
type = "doctest"
options = "+ELLIPSIS"
---

# Python support

Python support is provided by the Python runtime defined in
`groktest.python`.

Use `start_runtime` to create an initialized instance of a Python
runtime.

    >>> from groktest import start_runtime

    >>> python = start_runtime("python")

Confirm the runtime is available.

    >>> python.is_available()
    True

The runtime can be initialized for tests using `init_for_tests` and
providing init configuration.

    >>> python.init_for_tests({"python": {"init": "msg = 'Hi!'"}})

Create a helper to execute test expressions. We use the Python test spec
for parsing.

    >>> def run_test(s, options=None):
    ...     from groktest import parse_tests, PYTHON_SPEC
    ...     tests = parse_tests(s, PYTHON_SPEC, "<test>")
    ...     assert len(tests) == 1
    ...     result = python.exec_test_expr(tests[0], options or {})
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
    <BLANKLINE>

Without `pprint`:

    >>> run_test("""
    ... >>> {
    ... ...     "zzzzzzzzzzzzzzzzzz": 1,
    ... ...     "yyyyyyyyyyyyyyyyyy": 2,
    ... ...     "xxxxxxxxxxxxxxxxxx": 3
    ... ... }
    ... """)
    {'zzzzzzzzzzzzzzzzzz': 1, 'yyyyyyyyyyyyyyyyyy': 2, 'xxxxxxxxxxxxxxxxxx': 3}
    <BLANKLINE>

Note that `msg`, which we defined for the runtime using
`init_for_tests()` above, is available in globals.

    >>> run_test(">>> print(msg)")
    Hi!
    <BLANKLINE>
    
Stop the runtime.

    >>> python.stop()

Once shut down, the runtime is no longer available.

    >>> python.is_available()
    False
