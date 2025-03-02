# skip option

A test is skipped when `skip` is enabled.

    >>> 1  # +skip
    2

The last specified option determines the skip behavior.

    >>> 1  # +skip -skip
    1

    >>> 1  # +skip -skip +fails
    2

    >>> 1  # +skip -skip +skip
    2

If `skip` has a value, the value is used to read an environment
variable. If the environment variable is set and non-empty, `skip`
evaluates to true and the test is skipped.

The name may be prefixed with `!` to indicate the test should be skipped
if the env var is not set.

To illustrate, create a sample test that uses env vars to skip tests.

    >>> import tempfile, os

    >>> tmp = tempfile.mkdtemp(prefix="groktest-")
    >>> test_filename = os.path.join(tmp, "test.md")
    >>> _ = open(test_filename, "w").write("""
    ... >>> 1  # +skip=foo
    ... 2
    ... >>> 2  # +skip=!foo
    ... 1
    ... """)

Run the test without the `foo` env var.

    >>> run(
    ...     f"python -m groktest {test_filename} --show-skipped",
    ...     env={"foo": "", "NO_SAVE_LAST": "1"}
    ... )  # +wildcard
    Testing .../test.md
    **********************************************************************
    File ".../test.md", line 2
    Failed example:
        1  # +skip=foo
    Expected:
        2
    Got:
        1
    ----------------------------------------------------------------------
    1 test run
    1 test skipped
     - .../test.md:4
    1 test failed 💥 (see above for details)
     - .../test.md:2
    ⤶
    <1>

Run the test with `foo`.

    >>> run(
    ...     f"python -m groktest {test_filename} --show-skipped",
    ...     env={"foo": "1", "NO_SAVE_LAST": "1"}
    ... )  # +wildcard
    Testing .../test.md
    **********************************************************************
    File ".../test.md", line 4
    Failed example:
        2  # +skip=!foo
    Expected:
        1
    Got:
        2
    ----------------------------------------------------------------------
    1 test run
    1 test skipped
     - .../test.md:2
    1 test failed 💥 (see above for details)
     - .../test.md:4
    ⤶
    <1>
