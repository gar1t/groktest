---
[tool.groktest]

options = "+parse"
types.cat_or_dog = "cat|dog"
---

# Parse types

When `parse` is enabled, expected output may use format specs to match
test output.

By default `{}` matches anything up to the following expected text.

    >>> 'The cat walks on four paws'
    'The {} walks on {}'

A parse type may be included to match output to specific types. For a
list of supported types, see [this list](
https://github.com/r1chardj0n3s/parse#format-specification).

    >>> 'The cat walks on 4 paws'
    'The {} walks on {:d} paws'

Custom parse types can be registered in test config. Sample types are
defined in the front matter above.

    >>> 'The cat walks on two paws'
    'The {:cat_or_dog} walks on two paws'

    >>> 'The lion walks on two paws'  # +fails
    'The {:cat_or_dog} walks on two paws'

If a parse type is used that is undefined, Groktest lists it as the
reason for the error.

    >>> 'A sparrow'  # +fails
    'A {:bird}'
