# Pretty print results

Groktest supports pretty-printing Python using one of two methods: the
pprint module and json formatting. Pretty printing for each method is
enabled using `pprint` and `jprint` options respectively.

    >>> numbers = list(range(0, 1000000, 100000))

Without pretty printing:

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

With `json`:

    >>> numbers  # +json
    [
      0,
      100000,
      200000,
      300000,
      400000,
      500000,
      600000,
      700000,
      800000,
      900000
    ]

In both formats, keys are sorted.

    >>> map = {
    ...   "zzzzzzzzzz": 123,
    ...   "yyyyyyyyyy": 456,
    ...   "xxxxxxxxxx": 789,
    ...   "wwwwwwwwww": 321,
    ... }

    >>> map
    {'zzzzzzzzzz': 123, 'yyyyyyyyyy': 456, 'xxxxxxxxxx': 789, 'wwwwwwwwww': 321}


    >>> map  # +pprint
    {'wwwwwwwwww': 321,
     'xxxxxxxxxx': 789,
     'yyyyyyyyyy': 456,
     'zzzzzzzzzz': 123}

    >>> map  # +json
    {
      "wwwwwwwwww": 321,
      "xxxxxxxxxx": 789,
      "yyyyyyyyyy": 456,
      "zzzzzzzzzz": 123
    }

When using `pprint` or `json`, None values are also printed.

    >>> None  # +pprint
    None

    >>> None  # +json
    null
