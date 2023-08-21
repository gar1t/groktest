# Groktest To Do

## Error support

  - How do we explicitly handle an 'error' (non-zero code)
  - Consider Python (doctest as model) and also shell (`<exit N>` as
    optional last-line on success, required on error)

## Think about the `assert` pattern

This is messy:

    >>> foo < 33, foo
    (True, {})

This is better:

    >>> assert foo < 33

We just need decent error reporting in this case.

## Globals config

  - Project level
  - Front-matter

## Test options

  - Project level
  - Front-matter
  - Per test

Per test, `doctest` uses the `doctest: [+-]OPTION` pattern. We should
explore some alternatives.

Ideas:

    >>> print("a\nb")  # +diff

    >>> print("a\nb")  # +report=diff

    >>> print("a\nb")  #> {"report": "diff"}

    >>> print("a\nb")  #| report: diff

We should keep things simple. I don't think supporting JSON or YAML like
this is a good idea. A simple switch syntax should be fine.

    [-+] (?P<name>\w+) |
    [+]  (?P<name>\w+) = (?P<value>.+)

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


## Express opinions (blog post)

  - Documentation provides essential narrative and context for tests
  - Narrative and context eliminate non-obvious tests
  - Non-obvious tests are technical debt
    - Are they correct to begin with?
    - How must time does it take to answer this question?
    - When they break, what needs to change?
  - Source code should not contain tests
    - Should focus on specifying and solving problems
    - Tests clutter source code files with noise - move them to another
      location

pytest example:

        def test_answer():
    >       assert func(3) == 5
    E       assert 4 == 5
    E        +  where 4 = func(3)


doctest/Groktest:

    Failed example:
        func(3)
    Expected:
        5
    Got:
        4

## Property based testing (super speculative)

From the Quick Start
[example](https://hypothesis.readthedocs.io/en/latest/quickstart.html)
for [Hypothesis](https://hypothesis.readthedocs.io/), a PyTest style
test:

    @given(text())
    def test_decode_inverts_encode(s):
        assert decode(encode(s)) == s

The implementation in as a doc test:

    >>> @given(text())
    ... @example("")
    ... def decode_encode(s):
    ...     assert decode(encode(e)) == s

    >>> decode_encode()

While it's be nice to feature `assert decode(encode(e)) == s` as the
example, to do so requires a couple of unnatural steps:

 - An artificial var `s` needs to be defined
 - Some extra-Python spec needs to be invented to provide the test
   config

Something like this:

    >>> s = ""
    >>> assert decode(encode(s)) == s  #> @given(text())
    ...                                #> @example("")

This goes through mad hoops just to rephrase the test in a slightly more
doc friendly way. It's not a good trade off I think.
