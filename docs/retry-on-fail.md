# Retry on Fail

Some tests may occasionally fail due to environmental anomalies. For
example, an exceptionally slow test environment may cause tests that
rely on baseline performance to fail.

In such cases, it may be helpful to retry a test under an assumption
that the environmental conditions will change.

In general, however, avoid using this pattern. Write tests that are
robust to environment conditions.

To retry a test file on failure, set `retry-on-fail` to a number greater
than 0 as a test option.

For example, the following test file is configured to run a maximum of
three times --- the initial test plus two retries.

To illustrate, create tests that fail when certain files don't exist.
This simulates a dynamic test environment.

    >>> import tempfile
    >>> tmp = tempfile.mkdtemp(prefix="groktest-")
    >>> os.chdir(tmp)

    >>> with open("test.md", "w") as f:
    ...     _ = f.write("""
    ... ---
    ... test-options: +retry-on-fail=2
    ... ---
    ...
    ... >>> import os
    ... >>> one_exists = os.path.exists("1")
    ... >>> two_exists = os.path.exists("2")
    ...
    ... >>> one_exists
    ... True
    ...
    ... >>> two_exists
    ... True
    ...
    ... >>> if not one_exists:
    ... ...     open("1", "w").close()
    ... ... elif not two_exists:
    ... ...     open("2", "w").close()
    ... """)

Run the tests.

    >>> run(f"groktest {tmp}/test.md")  # +wildcard +diff
    Testing test.md
    **********************************************************************
    File ".../test.md", line 10
    Failed example:
        one_exists
    Expected:
        True
    Got:
        False
    **********************************************************************
    File ".../test.md", line 13
    Failed example:
        two_exists
    Expected:
        True
    Got:
        False
    Retrying test.md (1 of 2)
    **********************************************************************
    File ".../test.md", line 13
    Failed example:
        two_exists
    Expected:
        True
    Got:
        False
    Retrying test.md (2 of 2)
    ----------------------------------------------------------------------
    6 tests run
    All tests passed 🎉
    ⤶
    <0>
