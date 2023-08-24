# Groktest To Do

- Ignore exception detail by default and the `???` option to disable
  that
- Option based config of parse types (`types.name = <pattern>`)
- How to support type conversion for parser types?? Do we care?

## Tags and deps

Tags per test in front-matter.

```
---
tags = ["core", "unit", "blue"]
---
```

Run with tags:

    $ groktest . core

## Shell runtime

Time to start thinking about shell based runtimes.

- How to configure alongside default tests? What applied across
  runtimes, what doesn't?

- How to configure for different test types?

## Test options

Needed options (lower priority at this point):

- `solo`

  Run only tests enabled for solo, if any are enabled. Defaults to
  disabled.

  Soloing one or more tests is an easy way to run only certain tests.
  This is useful when debugging a failing test.

- `paths`

  Normalize paths to be `/` or `\`. Defaults to disabled and `/` if
  enabled without an explicit value.

## Reports

- Total number of tests
- Tests passed
- Tests failed
- Tests skipped

Cleanup test report scheme:

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

## Property based testing (speculative futurism)

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

## Assertions

This is okay:

    >>> assert x < 0, x

This is better:

    >>> assert x < 0

This may be even better:

    >>> x < 0

Could we create an option `assert` that considers `True` result to be a
pass and antying else to be a fail?

    >>> x < 0  # +assert

When defined in front matter, the assertions tokens go away.

This option would have to dig out the expression details and provide a
decent report. The implementation here is straight forward - use `ast`
to find names used in the expression and show their values in the
report.

I think the simplification of the expression comes with some confusion -
why isn't this expression evaluating to a boolean on success? Using
`assert` clears this up.

The winner:

    >>> assert x < 100

with a good report on the assertion failure. This could be behavior
that can be disabled with an option (e.g. `-assert`).

## Reports

- When we get to it, need a _good_ diff report that is _useful_
- Should be _one_ version of this - we don't need N failure diff
  reports
- By _good_ I mean it knows about wildcard matching and figures out
  how to show what caused the test to fail
- I think it should use color inline - the line by line diffs are too
  hard to read (maybe)
- This might be hard
