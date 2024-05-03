---
[tool.groktest]
options = "-wildcard"
---

This document is just used to illustrate front-matter config. It doesn't
define any tests.

The project config defines `+wildcard`, which is disabled above. The
test below should therefore fail.

    >>> "hello"  # +fails
    '...'
