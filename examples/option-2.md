---
option-functions: custom_types
---

`skip-red` option skips the test only when the value is `red`.

    >>> 1  # +skip-red=red
    2

    >>> 1  # +skip-red=yellow
    1

`table` normalizes table defs in a comparison.

    >>> print("""
    ... |------|---------|--------|
    ... | Name | Country | Height |
    ... |------|---------|--------|
    ... | Dog  | USA     | 2      |
    ... | Cat  | Mexico  | 1      |
    ... """.strip())  # +table
    |------|---------|--------|
    | Name | Country | Height |
    |------|---------|--------|
    | Dog  | USA     | 2      |
    | Cat  | Mexico  | 1      |
