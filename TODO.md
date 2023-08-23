# Groktest To Do

- Str matcher
- Test options - mainly interested in wildcard and whitespace

## Think about the `assert` pattern

This is messy:

    >>> foo < 33, foo
    (True, {})

This is better:

    >>> assert foo < 33

We just need decent error reporting in this case.

## Test options

- Project level
  - [ ] general
  - [ ] doctest

- Front-matter
  - [ ] general
  - [x] doctest

- Per test
  - [ ] general
  - [x] doctest

Per test, `doctest` uses the `doctest: [+-]OPTION` pattern. This is more
verbose than what we'd like.

Proposal is to use this pattern:

    [-+] (?P<name>\w+) |
    [+]  (?P<name>\w+) = ["']?(?P<value>.+)["']?

This supports negation or deletion of options using `-<name>` options
and enabling or setting options using `+<name>` and `+<name>=<value>`
respectively.

Examples:

    >>> print("{}")  # -parse
    {}

Needed options:

- `parse`

   Output is matched using the `parse` library. Disabled by default.

   Defaults to false to avoid collisions with curly braces, which are
   common in Python data representation.

   This should pass by default:

   ```
   >>> {"foo": 123}
   {"foo": 123}
   ```

   To pattern match this example, `+parse` is used with a modified
   example.

   ```
   >>> {"foo": 123}  # +parse
   {{"foo": {:d}}}
   ```

   As with any option, `parse` can be enabled for all tests using front
   matter.

   ```
   test-options: +parse
   ```

- `case`

  Output matching is case-sensitive. Enabled by default.

  Disable for case-insensitive matches using `-case`.

  ```
  >>> "Hello"  # -case
  'hello'
  ```

- `skip`

  Skips a test. Disabled by default.

  All tests in a test file can be skipped by enabling this option in
  front-matter. Individual tests can be unskipped using `-skip` in this
  case.

- `fails`

  Indicates that the test is expected to fail. Disabled by default.

  It can be useful to include tests that fail as examples. If the test
  succeeds unexpectedly, the success is recorded as a failure in the
  outout. Otherwise the test is considered to have passed.

  Similar in application to `+skip` but asserts an expected failure.

- `solo`

  Run only tests enabled for solo, if any are enabled. Defaults to
  disabled.

  Soloing one or more tests is an easy way to run only certain tests.
  This is useful when debugging a failing test.

- `blankline`

  A value specified the blank line marker. Default is config specific.

  E.g. `+blankline=<BLANKLINE>` set the `doctest` marker.

  Use `-blankline` to prevent use of blank lines in examples.

- `wildcard`

  Match any output using a wildcard token. Disabld by default.

  When enabled the configured wildcard will match any pattern up until
  the output following the wildcard token.

  The default wildcard token is `...`. Other test types may use
  different tokens.

  ```
  >>> print("Hello foo bar")  # +wildcard
  Hello ...
  ```

  The option may be used to set the token. For example `+wildcard=*`
  sets `*` as the wildcard.

  ```
  >>> print("Hello foo bar")  # +wildcard=*
  Hello *
  ```

  The wildcard can be configured for all tests in a test file using the
  file front matter.

- `whitespace`, `ws`

  Consider whitespace when comparing expected and test output. Enabled
  by default.

  To disregard whitespace in matches, disable the option using
  `-whitespace`.

- `paths`

  Normalize paths to be `/` or `\`. Defaults to disabled and `/` if
  enabled without an explicit value.

## Globals config

  - Project level
  - Front-matter

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
