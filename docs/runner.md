---
test-type: doctest
---

# Test runners

## Runner state

Runner state an internal construct Groktest uses when running tests.

    >>> from groktest import init_runner_state

    >>> state = init_runner_state("examples/defaults.md")

Runner state consists of the following:

- Test configuration
- Runtime
- Tests
- Results

    >>> state.config  # doctest: +ELLIPSIS
    <groktest.Config object at ...>

    >>> state.runtime  # doctest: +ELLIPSIS
    <groktest.python.PythonRuntime object at ...>

    >>> state.tests  # doctest: +ELLIPSIS
    [<groktest.Test object at ...>, ...]

    >>> state.results
    {'failed': 0, 'tested': 0}

The runtime available from the state is available.

    >>> state.runtime.is_available()
    True

Runtime should be shut down when no longer needed.

    >>> state.runtime.shutdown()

## Errors

A file must exist.

    >>> init_runner_state("does_not_exist")
    ... # doctest.IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    FileNotFoundError: [Errno 2] No such file or directory: 'does_not_exist'
