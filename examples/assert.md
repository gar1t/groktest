# Using `assert` in tests

Assertions are useful for testing values that aren't suitable for
test-by-example. Value ranges are a good example.

Take `x`, which should be between `0` and `100` inclusive.

    >>> x = 50

We can't provide an example to confirm `x` is in the expected range.
This is where `assert` is useful.

    >>> assert 0 <= x <= 100

What happens when the assertion fails?

    >>> x = 101

    >>> assert 0 <= x <= 100
    Traceback (most recent call last):
    AssertionError: {'x': 101}

Groktest applies special handling to the assertion failure - it provides
a dict of named values used in the expression. This can be used to
diagnose the failure.

Alternatively, the test itself may provide diagnostic information. In
this case, Groktest does not  modify the assertion error.

    >>> assert 0 <= x <= 100, x
    Traceback (most recent call last):
    AssertionError: 101
