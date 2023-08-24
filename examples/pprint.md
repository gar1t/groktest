# Pretty print results

Groktest ...

    >>> numbers = list(range(0, 1000000, 100000))

Without `pprint`:

    >>> numbers
    [0, 100000, 200000, 300000, 400000, 500000, 600000, 700000, 800000, 900000]

With `pprint`:

    >>> numbers  # +pprint
    [0,
     100000,
     200000,
     300000,
     400000,
     500000,
     600000,
     700000,
     800000,
     900000]
