# Groktest To Do

- Use Groktest to test itself
  - Move docs to groktest
  - Make sure we have doctest coverage elsewhere

- Ignore exception detail by default and `-error-detail` option to
  disable that?

- `--last-failed` option

- Consider an `any` type or a type that matches non line endings.

- Remove Groktest from stack:

    Traceback (most recent call last):
      File "/home/garrett/Code/groktest/groktest/python.py", line 241, in _handle_test
        _exec_test(test, globals)
      File "/home/garrett/Code/groktest/groktest/python.py", line 284, in _exec_test
        result = eval(code, globals)

- Platform specific tests (Windows only, etc.)
- Handle platform specific paths - e.g. a `path` option
- How would someone define/implement a custom options?
  - Formatting expected/actual
  - Alternative matching?

- Support KeyboardInterrupt

- Apply `--last` to a project (save file is per project)

- Support debugging (i.e. calls to `breakpoint()` should work!)

- Nushell should retain vars across tests

- Look for other project config toml files not just pyproject! E.g.
  `Cargo.toml` is used for Rust projects. What other project config toml
  files are there? (this is hacked for Cargo.toml but it needs cleanup:
  consolidate logic of finding a project toml and figure out a
  generalized pattern rather than hard coding filenames - unless there
  is no standard and there are only a couple toml files - but what about
  a shell project??)

- Whitespace on right of line cannot be matched - how does doctest
  handle this? Auto strip? We need a marker like blankline.

- Use rich for progress (useful for parallel tests when they land)

## Tags and deps

Tags per test in front-matter.

```
---
tags = ["core", "unit", "blue"]
---
```

Run with tags:

    $ groktest . core

Test files could have dependencies on other files. When you run one it
causes others to run. If upstream tests fail, downstream tests are
skipped.

This is how we can implement uat alongside the other tests. E.g. do we
need to waste time running 'aws' tests if 'core' tests have failed?
Also, some tests may rely on setup performed by upstream tests.

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
- Modernize Groktest reports
- Test results as dict is lame - we should type this
- Should know about skipped tests

## Parallel run support

- Per file is easy - it's isolated per runtime
- Use technique used in Guild - simple and it works
- Use rich progress for concurrent progress status

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

      >>> # -skiprest

## Property based testing (speculative futurism)

These tests are skipped as they're purely speculative.

    >>> # +skiprest

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

## Reports

- When we get to it, need a _good_ diff report that is _useful_
- Should be _one_ version of this - we don't need N failure diff
  reports
- By _good_ I mean it knows about wildcard matching and figures out
  how to show what caused the test to fail
- I think it should use color inline - the line by line diffs are too
  hard to read (maybe)
- This might be hard

## Re-binding matched names with checks

Currently a re-binding of a parsed value simply updates the global
state. I think this is wrong - it should only update if the variable is
not previously bound. Further, Groktest should consider the test a
failure if the re-binding attempts to change the current value.

Here's an example.

    >>> print("Hello Joe")  # +parse
    Hello {name}

    >>> name
    'Joe'

    >>> print("Hello Mike")  # +parse
    Hello {name}

    >>> name
    'Mike'

  This is no good! The test that attempts the second binding should fail
  in its attempt to update `name` with any value other than `'Joe'`.

  Steps to implement:

  - A call to `state.runtime.handle_test_match(match)` should be capable
    of failing with some message - in particular a 'variable match'
    error or something to that effect.

  - If the call fails, the test fails.

  - The Python runtime, which has access to the globals and is
    responsible for updating globals with 'vars' should refuse to update
    a var with a new value. Matching values are okay!

This will provide an excellent assertion ability based on pattern
matching! This should be a 1.0 feature.

## Smart suite testing

When running a suite of tests (currently, project-defined tests),
Groktest should keep track of staleness and only run test docs that need
to run.

A stale test doc is:

- One that has not been run or had any failures on the last run
- One whose dependencies have changed since its last run

How calculate dependencies?

Short of some clever (and probably brittle) sniffing of read flags,
there seems two options:

1. Don't bother with dependencies apart from the test doc file itself

2. Consider all non test docs under the project to be required and if
   any are modified, consider the test stale (implication obviously is
   that any change to any non test file invalidates all prior test
   results, which is pretty extreme)

Is there simply a switch we can use (e.g. `--needed` or `--cache`) to
say, "remember the last result and re-run if there was a failure or the
test has been changed".

Then one could create a second "Run All Tests" task that uses this mode.
E.g. "Run All Tests (cached)"

Something like this is needed as it's a) very handy to "run all tests"
at a whim to make sure everything is passing and b) very time consuming
to actually run all tests. Short of this, one needs to "run all tests",
note the failure docs, then re-run those individually until each passes.
Total pain.
