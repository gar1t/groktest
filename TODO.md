# Groktest To Do

- Project config for doctest options

## Error support

- How do we explicitly handle an 'error' (non-zero code)
- Consider Python (doctest as model) and also shell (`<exit N>` as
  optional last-line on success, required on error)

`doctest` shows something like this:

```
Failed example:
    groktest.DEFAULT_CONFIG.ps1
Exception raised:
    Traceback (most recent call last):
      File "/usr/lib/python3.10/doctest.py", line 1350, in __run
        exec(compile(example.source, filename, "single",
      File "<doctest parsing.md[0]>", line 1, in <module>
        groktest.DEFAULT_CONFIG.ps1
    NameError: name 'groktest' is not defined
```

There's an explicit notion of 'error' here. The report does not show
output printed to standard outout during the evaluation of the
expression.

When an exception doesn't occur, output looks like this:

```
Failed example:
    1
Expected:
    2
Got:
    1
```

We *could* implement something like this:

```
Failed example:
    groktest.DEFAULT_CONFIG.ps1
Expected nothing
Got:
    Traceback (most recent call last):
      File "/usr/lib/python3.10/doctest.py", line 1350, in __run
        exec(compile(example.source, filename, "single",
      File "<doctest parsing.md[0]>", line 1, in <module>
        groktest.DEFAULT_CONFIG.ps1
    NameError: name 'groktest' is not defined
```

In the case of `shell`, we could face something similar, where non-zero
exit is an 'error'.

```
Failed example:
    echo Boom
    exit 1
Exit (1):
    Boom
```

If it were an empty result:

```
Failed example:
    exit 1
Exit (1)
```

If we used the expected/got idiom the report might look like this:

```
Failed example:
  echo Boom
  exit 1
Expected:
  Boom
  <exit 0>
Got:
  Boom
  <exit 1>
```

I don't really see the point of treating an error differently. The
`doctest` method loses the 'expected' report and sets the pattern up for
other runtimes.

I believe this is simply a reporting topic.

Let's proceed with the got/expected pattern for errors, as well as
success (treating them as no different, except possibly some
reformatting).

## Think about the `assert` pattern

This is messy:

    >>> foo < 33, foo
    (True, {})

This is better:

    >>> assert foo < 33

We just need decent error reporting in this case.

## Test options

- Project level
- Front-matter
- Per test

Per test, `doctest` uses the `doctest: [+-]OPTION` pattern. This is more
verbose than what we'd like.

Proposal is to use this pattern:

    [-+] (?P<name>\w+) |
    [+]  (?P<name>\w+) = (?P<value>.+)

This supports negation or deletion of options using `-<name>` options
and enabling or setting options using `+<name>` and `+<name>=<value>`
respectively.

Examples:

    >>> print("{}")  # -match
    {}

Needed options:

- `match`

   Output is patterns are matched. Disabled by default.

   Defaults to false to avoid collisions with curly braces, which are
   common in Python data representation.

   This should pass by default.

   ```
   >>> {"foo": 123}
   {"foo": 123}
   ```

   To pattern match this example, `+match` is used with a modified
   example.

   ```
   >>> {"foo": 123}  # +match
   {{"foo": {:d}}}
   ```

- `case`

  Output matching is case-sensitive. Enabled by default.

  Disable for case-insensitive matches.

  ```
  >>> "Hello"  # -case
  hello
  ```

- `skip`

  Skips a test. Disabled by default.

  An entire test file can be skipped by enabling this option in
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
