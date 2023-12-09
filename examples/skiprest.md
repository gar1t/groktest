# skiprest option

The `skiprest` option skips the current test and all subsequent tests.

Tests are not skipped by default.

    >>> 1
    1

    >>> 1  # +fails
    2

Use `skiprest` to skip current and remaining tests.

    >>> 1  # +skiprest
    2

    >>> 2
    3

`skiprest` can be disabled using `-skiprest`.

    >>> 1  # -skiprest
    1

    >>> 2  # +fails
    3

To disable blocks of tests, use `+skiprest` and `-skiprest` to start and
end the skipped block respectively.

    >>> # +skiprest

    >>> 1
    2

    >>> 2
    3

    >>> # -skiprest

    >>> 1
    1

    >>> 2  # +fails
    3
