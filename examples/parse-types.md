---
test-options = "+parse"

[parse-types]
cat_or_dog = "cat|dog"
mm = "\\d+ mm"
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

Another type, which matches `N mm`:

    >>> 'The width should be 22 mm'
    'The width should be {:mm}'

The patter can be used to bind matched output to a variable.

    >>> 'The width should be 45 mm'
    'The width should be {width:mm}'

    >>> width
    '45 mm'
