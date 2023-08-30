---
test-options: +wildcard
---

# Testing for errors

Groktest applies special handling to errors raised when evaluating a
test. An 'error' is runtime specific. In the case of Python, an error
occurs when an exception is raised during evaluation of the test
expression.

Define a function that generates an error. The function imports a
locally defined Python module to introduce additional calls for error
detail (tracebacks).

    >>> def boom():
    ...     import sys, os
    ...     sys.path.append(os.path.dirname(__file__))
    ...     import util
    ...     util.boom()

To test for an error, the author has two choices: provide a full error
report or provide a "short error". In the case of Python errors, a short
error contains only the traceback heading and the error value - the call
stack for the error is omitted.

Handle a short error.

    >>> boom()
    Traceback (most recent call last):
    ZeroDivisionError: division by zero

To handle the full error, include the error details. In the case of
Python, error details consist of the error call stack.

    >>> boom()  # +diff
    Traceback (most recent call last):
      File ".../examples/errors.md", line ..., in <module>
        boom()  # +diff
      File ".../examples/errors.md", line ..., in boom
            util.boom()
      File ".../examples/util.py", line ..., in boom
        return 1 / 0
    ZeroDivisionError: division by zero

Full errors may contain absolute paths to source code files and line
numbers. It's typically necessary to pattern match these using either
wildcards or parse patterns when providing error details.

Other examples:

    >>> raise ValueError("a\nb\nc")  # +wildcard
    Traceback (most recent call last):
      File ".../examples/errors.md", line ..., in <module>
        raise ValueError("a\nb\nc")  # +wildcard
    ValueError: a
    b
    c

    >>> raise ValueError("a\nb\nc")
    Traceback (most recent call last):
    ValueError: a
    b
    c

Exception values that contain indented lines:

    >>> raise ValueError("a\n  b\nc")  # +wildcard
    Traceback (most recent call last):
      File ".../examples/errors.md", line ..., in <module>
        raise ValueError("a\n  b\nc")  # +wildcard
    ValueError: a
      b
    c

    >>> raise ValueError("a\n  b\nc")  # +parse
    Traceback (most recent call last):
      File "{}/examples/errors.md", line {:d}, in <module>
        raise ValueError("a\n  b\nc")  # +parse
    ValueError: a
      b
    c

    Traceback (most recent call last):
    ValueError: a
      b
    c
