# Fail Fast Option

The CLI supports a `--fail-fast` option.

Run the `fail-fast.md` example normally.

    >>> run("groktest examples/fail-fast.md")  # +wildcard +paths +diff
    Testing examples/fail-fast.md
    **********************************************************************
    File ".../fail-fast.md", line 5
    Failed example:
        1
    Expected:
        2
    Got:
        1
    **********************************************************************
    File ".../examples/fail-fast.md", line 8
    Failed example:
        2
    Expected:
        3
    Got:
        2
    ----------------------------------------------------------------------
    2 tests run
    2 tests failed 💥 (see above for details)
     - examples/fail-fast.md:5
     - examples/fail-fast.md:8
    ⤶
    <1>

Run with `--fail-fast`.

    >>> run("groktest examples/fail-fast.md --fail-fast")  # +wildcard +paths +diff
    Testing examples/fail-fast.md
    **********************************************************************
    File ".../examples/fail-fast.md", line 5
    Failed example:
        1
    Expected:
        2
    Got:
        1
    ----------------------------------------------------------------------
    1 test run
    1 test skipped (use --show-skipped to view)
    1 test failed 💥 (see above for details)
     - examples/fail-fast.md:5
    ⤶
    <1>
