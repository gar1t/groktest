---
test-options: +skip
---

By default the tests in this document are skipped.

    >>> 1 + 2
    4

    >>> print("Hello")
    Goodbye

Individual tests can be enabled with `-skip`.

    >>> 1 + 2  # -skip
    3
