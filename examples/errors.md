---
test-options: +wildcard
---

# Handling errors generated by tests (Python)

Groktest doesn't apply special handling for errors in the way that
`doctest` does. If an error occurs, its traceback is used as outout.

    >>> def boom():
    ...     import sys, os
    ...     sys.path.append(os.path.dirname(__file__))
    ...     import util
    ...     util.boom()

  By default test detail is omitted from output.

    >>> boom()
    Traceback (most recent call last):
    ZeroDivisionError: division by zero

  To show error detail, enable `error-detail`.

    >>> boom()  # +error-detail +diff
    Traceback (most recent call last):
      File ".../examples/errors.md", line ..., in <module>
        boom()  # +error-detail +diff
      File ".../examples/errors.md", line ..., in boom
            util.boom()
      File ".../examples/util.py", line ..., in boom
        return 1 / 0
    ZeroDivisionError: division by zero

Other examples:

    >>> raise ValueError("a\nb\nc")
    Traceback (most recent call last):
    ValueError: a
    b
    c

    >>> raise ValueError("a\nb\nc")  # +error-detail
    Traceback (most recent call last):
      File ".../examples/errors.md", line ..., in <module>
        raise ValueError("a\nb\nc")  # +error-detail
    ValueError: a
    b
    c

Exception values that contain indented lines are displayed correctly.

    >>> raise ValueError("a\n  b\nc")
    Traceback (most recent call last):
    ValueError: a
      b
    c