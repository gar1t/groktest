# Fail Fast Option

The CLI supports a `--failfast` option, which in turn configured a
`+failfast` test option.

When `failfast` is enabled, the tests are stopped after the first
failure.

Run the `failfast.md` example without failfast.

    >>> run("groktest examples/failfast.md")  # +wildcard +paths
    Testing examples/failfast.md
    **********************************************************************
    File ".../failfast.md", line 5
    Failed example:
        1
    Expected:
        2
    Got:
        1
    **********************************************************************
    File ".../examples/failfast.md", line 8
    Failed example:
        2
    Expected:
        3
    Got:
        2
    ----------------------------------------------------------------------
    2 tests run
    2 tests failed in 1 file 💥 (see above for details)
     - examples/failfast.md
    ⤶
    <1>

Run with `--failfast`.

    >>> run("groktest examples/failfast.md --failfast")  # +wildcard +paths
    Testing examples/failfast.md
    **********************************************************************
    File ".../examples/failfast.md", line 5
    Failed example:
        1
    Expected:
        2
    Got:
        1
    ----------------------------------------------------------------------
    1 test run
    1 test skipped
    1 test failed in 1 file 💥 (see above for details)
     - examples/failfast.md
    ⤶
    <1>
