---
[tool.groktest]
options = "+wildcard"
---

# Using `assert` in tests

Assertions are useful for testing values that aren't suitable for
test-by-example. Value ranges are a good example.

Take `x`, which should be between `0` and `100` incluive.

    >>> x = 50

We can't provide an example to confirm `x` is in the expected range.
This is where `assert` is useful.

    >>> assert 0 <= x <= 100

What happens when the assertion fails?

    >>> x = 101

In the case above, we just get this:

    >>> assert 0 <= x <= 100
    Traceback (most recent call last):
    AssertionError

This output doesn't tell us anything about `x`.

In this case, we should use a second term in the `assert` statement that
provides diagnistic values.

    >>> assert 0 <= x <= 100, x
    Traceback (most recent call last):
    AssertionError: 101

With this report, we know `x` is 101 and can take appropriate next steps
to fix the code or the test.
