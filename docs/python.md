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

Use the runtime to run tests.

    >>> from groktest import parse_tests

    >>> tests = parse_tests("""
    ... >>> 1 + 1
    ... 2
    ... """, PYTHON_CONFIG, "<test>")

    >>> result = python.run_test(tests[0])

    >>> result.code
    0

    >>> result.output
    '2\n'

Shut down the runtime.

    >>> python.shutdown()

Once shut down, the runtime is no longer available.

    >>> python.is_available()
    False
