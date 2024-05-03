# Reporting

Groktest currently reports results during a test run by printing
directly to standard output. Future enhancements will create a reporting
layer that can be used to customize the way Groktest presents results.

Reflecting the current closed nature of reporting, these tests work with
private functions.

Reporting is performed on test results. A handled result is one of the
following:

- Test passes, expected pass
- Test passes, expected fail
- Test fails, expected fail
- Test fails, expected pass

For tests, create a runner state that uses a Python runtime.

    >>> from groktest import RunnerState, PYTHON_SPEC, start_runtime
    >>> runtime = start_runtime(PYTHON_SPEC.runtime)
    >>> state = RunnerState([], runtime, PYTHON_SPEC, {"sep": False}, "<test>")

Function to test an example and print a result.

    >>> def test(expr, expected, options=None, lineno=1):
    ...     from groktest import Test, run_test
    ...     options = options or {}
    ...     test = Test(expr, expected, "<test>", lineno, {})
    ...     run_test(test, {**options, "sep": False}, state)

## Passing tests

By default Groktest doesn't print anything when a test passes.

    >>> test("1", "1")

However, Groktest provides the `fails` option, which signifies that a
test is expected to fail. When enabled, a test that passes is considered
a failure and one that fails is considered a success.

    >>> test("1", "1", {"fails": True})
    File "<test>", line 1
    Failed example:
        1
    Expected test to fail but passed

Line number is specified in the call to run the test.

    >>> test("1", "1", {"fails": True}, lineno=2)
    File "<test>", line 2
    Failed example:
        1
    Expected test to fail but passed

## Test errors

When a test fails, Groktest shows a comparison between the expected
result and the actual result. It supports two modes: expected-got and
diff.

Expected-got mode shows the test expected output and what the evaluated
expression generates ("got").

    >>> test("1", "2")
    File "<test>", line 1
    Failed example:
        1
    Expected:
        2
    Got:
        1

Diff mode shows a unified diff of expected and actual.

    >>> test("1", "2", {"diff": True})
    File "<test>", line 1
    Failed example:
        1
    Differences between expected and actual:
       @@ -1 +1 @@
       -2
       +1

When either expected or actual output is unspecified, the report states
that it expected or got "nothing" respectively.

    >>> test("None", "2")
    File "<test>", line 1
    Failed example:
        None
    Expected:
        2
    Got nothing

    >>> test("1", "")
    File "<test>", line 1
    Failed example:
        1
    Expected nothing
    Got:
        1

## Blank lines

Blank lines present a special case in Groktest. Expected output is
delimited by a blank line or a PS1 prompt. To represent blank lines,
expected output must use a blank line symbol. This is ⤶ (U+2936) by
default.

    >>> test("print('')", "⤶")

This character is used to show test output ("got") rather than a literal
blank line.

    >>> test("print('')", '')
    File "<test>", line 1
    Failed example:
        print('')
    Expected nothing
    Got:
        ⤶

The blank line marker is configured using the 'blankline' option.

    >>> test("print('')", '<blank>', {"blankline": "<blank>"})

    >>> test("print('')", '', {"blankline": "<blank>"})
    File "<test>", line 1
    Failed example:
        print('')
    Expected nothing
    Got:
        <blank>

Support for blank lines can be disabled. It's not possible to support
blank line matching in this case.

    >>> test("print('')", '', {"blankline": False})
    File "<test>", line 1
    Failed example:
        print('')
    Expected nothing
    Got:
    ⤶

Disabling blankline is useful in the rare case where `⤶` is used in the
expected output.

Without disabling or changing the blank line support, this example fail:

    >>> test("print('⤶')", "⤶")
    File "<test>", line 1
    Failed example:
        print('⤶')
    Expected:
        ⤶
    Got:
        ⤶

In this case it succeeds:

    >>> test("print('⤶')", "⤶", {"blankline": False})

## Transforming options

A number of options effect the way results are compared. These options
either transform both expected and actual output or apply pattern
matching as specified in the expected output to actual output.

When tests fail in the context of these options, the error report may be
difficult to use to find differences.

The following options affect error reports in this way:

- `parse`
- `wildcard`
- `case`
- `space`

### Parse

When `parse` is enabled, Groktest applies its most flexible pattern
matching algorithm to test the actual output. It currently does not
provide details on why output doesn't match.

    >>> test("'The number is {:d}'", "'The number is ten'", {"parse": True})
    File "<test>", line 1
    Failed example:
        'The number is {:d}'
    Expected:
        'The number is ten'
    Got:
        'The number is {:d}'

In this case, the user must compare expected and actual output and
determine that the parse type `d` cannot match `'ten'` because it only
matches integers. It would be helpful if Groktest isolated the pattern
mismatch and offered information to help troubleshoot the problem.

### Wildcard

The `wildcard` option presents a simplified alternative to `parse` in
cases where any text can be matched.

    >>> test("""
    ... print('''1
    ... 2
    ... 3
    ... 5
    ... 4''')""",
    ... """1
    ... 2
    ... ...
    ... 5""",
    ... {"wildcard": True})
    File "<test>", line 1
    Failed example:
        print('''1
        2
        3
        5
        4''')
    Expected:
        1
        2
        ...
        5
    Got:
        1
        2
        3
        5
        4
