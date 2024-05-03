# Matching test results

## String matching

String matching is used by default. It's implemented by
`groktest.str_match`.

    >>> def str_match(expected, test_output, options=None):
    ...     from groktest import str_match as str_match0
    ...     m = str_match0(expected, test_output, options)
    ...     return m.match

By default, string matching simply compares two strings.

    >>> str_match("", "")
    True

    >>> str_match("1", "1")
    True

    >>> str_match("1", "2")
    False

    >>> str_match("a", "a")
    True

    >>> str_match("a", "A")
    False

### String matching and case

The `case` option determines if a match is case sensitive. By default,
matches are case sensitive - i.e. `case` is enabled.

    >>> str_match("a", "A")
    False

When `case` is disabled, matching is case insensitive.

    >>> str_match("a", "A", {"case": False})
    True

    >>> str_match(
    ...     "The quick brown fox",
    ...     "THE qUicK BroWN fOX",
    ...    {"case": False}
    ... )
    True

### String matching and white space

### String matching and wildcards

If `wildcard` is specified, the specified token is used to match any
output up to the output following the wildcard.

A single wildcard matches everything.

    >>> str_match("...", "Anything here matches", {"wildcard": "..."})
    True

The wildcard can be any series of characters.

    >>> str_match("?", "Anything here matches", {"wildcard": "?"})
    True

    >>> str_match("? b ?", "a b c", {"wildcard": "?"})
    True

Spaces are included in matches.

    >>> str_match("? b ?", "b", {"wildcard": "?"})
    False

    >>> str_match("? b ?", " b ", {"wildcard": "?"})
    True

Other wildcard examples.

    >>> str_match("aa...a", "aaa", {"wildcard": "..."})
    True

    >>> str_match("aa...aa", "aaa", {"wildcard": "..."})
    False

    >>> str_match(
    ...     "The ... is blue",
    ...     "The ball is blue",
    ...     {"wildcard": "..."}
    ... )
    True

The token is consumed from left to right.

    >>> str_match("....", "Hello.", {"wildcard": "..."})
    True

    >>> str_match("....", ".Hello", {"wildcard": "..."})
    False

## Parse matching

Groktest's `parse` option enables parse matching. Parse matching is
implemented by `groktest.parse_match`.

Create a proxy for runner state, which is used by the `parse_match`
function.

    >>> class StateProxy:
    ...     def __init__(self, config):
    ...         from groktest import _parse_type_functions
    ...         self.parse_functions = _parse_type_functions(config)

    >>> def match(expected, test_output, options=None, types=None):
    ...     from groktest import parse_match
    ...     config = {"parse": {"types": types}} if types else {}
    ...     state = StateProxy(config)
    ...     m = parse_match(expected, test_output, options, state)
    ...     print(m.vars if m.match else None)

Match simple output.

    >>> match("1", "1")
    {}

Use format expressions.

    >>> match("{}", "1")
    {}

    >>> match("{:d}", "1")
    {}

    >>> match("{:D}", "1")
    None

    >>> match("A {} cat", "A blue cat")
    {}

    >>> match("A {} cat", "A red cat")
    {}

    >>> match("A {} cat", "A red dog")
    None

    >>> match("A {} cat", "A blue and red cat")
    {}

    >>> match("A {:w} cat", "A blue and red cat")
    None

Use variables.

    >>> match("{x:d}", "1")
    {'x': 1}

    >>> match("A {desc} cat", "A blue cat")
    {'desc': 'blue'}

    >>> match("A {desc} cat", "A blue and red cat")
    {'desc': 'blue and red'}

Groktest match support can be customized with custom match types.

    >>> match(
    ...     "A {:color} cat",
    ...     "A blue cat",
    ...     types={"color": "blue|red"}
    ... )
    {}

    >>> match(
    ...     "A {color:color} cat",
    ...     "A red cat",
    ...     types={"color": "blue|red"}
    ... )
    {'color': 'red'}

    >>> match(
    ...     "A {:color} cat",
    ...     "A green cat",
    ...     types={"color": "blue|red"}
    ... )
    None

By default matches are case sensitive.

    >>> match("Hello", "hello")
    None

Compare with case insensitive.

    >>> match("Hello", "hello", options={"case": False})
    {}

Patterns match across multiple lines.

    >>> match(
    ... """
    ... Traceback (most recent call last):
    ... {stack}
    ... ZeroDivisionError: division by zero
    ... """,
    ... """
    ... Traceback (most recent call last):
    ... File "<stdin>", line 1, in <module>
    ... File "<stdin>", line 2, in boom
    ... ZeroDivisionError: division by zero
    ... """
    ... )  # -space
    {'stack': 'File "<stdin>", line 1,
               in <module>\nFile "<stdin>", line 2, in boom'}

Non-patterns are sensitive to line-endings.

    >>> match("a b", "a\nb")
    None

    >>> match("a b", "\na b\n")
    None

To match the previous example, the leading and trailing line-endings
need to be stripped.

    >>> match("a b", "\na b\n".strip())
    {}

### Parse matching and case

### Parse matching and white space

### Parse matching and error detail
