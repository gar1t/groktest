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

Use `__abc123__` as a sample environment variable to determine whether a
test is skipped.

Verify the value isn't set.

    >>> import os  # -skip
    >>> os.getenv("__abc123__")  # +pprint
    None

    >>> 1  # +skip=__abc123__ +fails
    2

Set the environment variable to a non-empty value.

    >>> os.environ["__abc123__"] = "1"
    >>> os.getenv("__abc123__")
    '1'

Skip using the environment variable.

    >>> 1  # +skip=__abc123__ +fails
    2

Reset the environment.

    >>> del os.environ["__abc123__"]
    >>> os.getenv("__abc123__")  # +pprint
    None
