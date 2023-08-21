# Groktest To Do

- Error support
  - How do we explicitly handle an 'error' (non-zero code)
  - Consider Python (doctest as model) and also shell (`<exit N>` as
    optional last-line on success, required on error)

- Cleanup test report scheme
  - Generalize (e.g. reporter/callback facility)
  - Modernize Grokville reports

- Test result refactor
  - Test results as dict is lame - we should type this
  - Should know about skipped tests

- Final tests results should report
  - Total number of tests
  - Tests passed
  - Tests failed
  - Tests skipped

- Method to quickly disable tests at a point
  - Some sort of test option
  - Note in output that tests were skipped (much better than renaming
    the prompt)

```
This test is fine.

    >>> 1 + 1
    2

`missing()` is broke - we don't want to run it, nor do we want to run
any past it. Use an empty test with a `skiprest` test option.

    >>> # +skiprest

    >>> missing()  # Would not be run - could alternatively +skip it
    Traceback (most recent call last):
    NameError: name 'missing' is not defined

```
