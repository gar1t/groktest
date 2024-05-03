# Named Functions

Groktest supports module-defined parse and option functions. Importing
of these functions is implemented by `_iter_named_functions`.

    >>> from groktest import _iter_named_functions as funs

Get parse functions:

    >>> list(funs(["custom_types"], ["examples"], "parse_", "type_name"))
    ... # -space +wildcard
    [('ver', <function parse_ver at ...>),
     ('loud', <function parse_upper at ...>)]

Get option functions:

    >>> list(funs(["custom_types"], ["examples"], "option_", "option_name"))
    ... # -space +wildcard
    [('skip-red', <function option_skip_red at ...>)]
