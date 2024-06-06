# Test runners

## Runner state

Runner state an internal construct Groktest uses when running tests.

    >>> from groktest import init_runner_state

    >>> state = init_runner_state("examples/defaults.md")

Runner state consists of the following:

- Test spec

    >>> state.spec  # +wildcard
    <groktest.TestSpec object at ...>

- Runtime

    >>> state.runtime  # +wildcard
    <groktest.python.PythonRuntime object at ...>

- Tests

    >>> state.tests  # +wildcard
    [<groktest.Test object at ...>, ...]

- Results

    >>> state.summary
    <TestSummary failed=0 tested=0 skipped=0>

The runtime available from the state is available.

    >>> state.runtime.is_available()
    True

Runtime should be stopped when no longer needed.

    >>> state.runtime.stop()

## Errors

A file must exist.

    >>> init_runner_state("does_not_exist")  # +wildcard
    Traceback (most recent call last):
    ...
    FileNotFoundError: [Errno 2] No such file or directory: '...does_not_exist'
