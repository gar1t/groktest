# Groktest To Do

- Ignore exception detail by default and the `???` option to disable
  that
- Option based config of parse types (`types.name = <pattern>`)
- How to support type conversion for parser types?? Do we care?

## Test options

Needed options:

- `solo`

  Run only tests enabled for solo, if any are enabled. Defaults to
  disabled.

  Soloing one or more tests is an easy way to run only certain tests.
  This is useful when debugging a failing test.

- `paths`

  Normalize paths to be `/` or `\`. Defaults to disabled and `/` if
  enabled without an explicit value.

## Final tests results should report

  - Total number of tests
  - Tests passed
  - Tests failed
  - Tests skipped

## Cleanup test report scheme

  - Generalize (e.g. reporter/callback facility)
  - Modernize Grokville reports
  - Test results as dict is lame - we should type this
  - Should know about skipped tests

## Parallel run support

  - Per file is easy - it's isolated per runtime
  - Use technique used in Guild - simple and it works

## Method to quickly disable tests at a point

  - Some sort of test option
  - Note in output that tests were skipped (much better than renaming
    the prompt)

    This test is fine.

        >>> 1 + 1
        2

    `missing()` is broke - we don't want to run it, nor do we want to
    run any past it. Use an empty test with a `skiprest` test option.

        >>> # +skiprest

        >>> missing()  # Would not be run - could alternatively +skip it
        Traceback (most recent call last):
        NameError: name 'missing' is not defined

## Property based testing

From the Quick Start
[example](https://hypothesis.readthedocs.io/en/latest/quickstart.html)
for [Hypothesis](https://hypothesis.readthedocs.io/), a PyTest style
test:

```python
@given(text())
@example("")
def test_decode_encode(s):
    assert decode(encode(s)) == s
```

As a doc test:

    >>> @given(text())
    ... @example("")
    ... def decode_encode(s):
    ...     assert decode(encode(e)) == s

    >>> decode_encode()

It'd be nice to feature `assert decode(encode(e)) == s` as the example.

    >>> assert decode(encode(s)) == s # +given s = text(), example('')

Not bad.
