---
test-type = "doctest"
---

# Matching test results

## String matching

String matching is used by default. It's implemented by
`groktest.str_match`.

    >>> def str_match(expected, test_output, options=None):
    ...     from groktest import str_match as str_match0
    ...     m = str_match0(expected, test_output, options)
    ...     pprint(m.match)

By default matched are exact.

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

If `case` is disabled, matches are case insensitive.

    >>> str_match("a", "A", {"case": False})
    True

If `wildcard` is specified, the specified token is used to match any
output up to the output following the wildcard.

A single wilcard matches everything.

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

Grokville's `parse` option enables parse matching. Parse matching is
implemented by `groktest.parse_match`.

    >>> def parse_match(expected, test_output, options=None, types=None):
    ...     from groktest import parse_match as parse_match0
    ...     config = {"parse": {"types": types}} if types else {}
    ...     m = parse_match0(expected, test_output, options, config)
    ...     pprint(m.vars if m.match else None)

Match simple output.

    >>> parse_match("1", "1")
    {}

Use format expressions.

    >>> parse_match("{}", "1")
    {}

    >>> parse_match("{:d}", "1")
    {}

    >>> parse_match("{:D}", "1")
    None

    >>> parse_match("A {} cat", "A blue cat")
    {}

    >>> parse_match("A {} cat", "A red cat")
    {}

    >>> parse_match("A {} cat", "A red dog")
    None

    >>> parse_match("A {} cat", "A blue and red cat")
    {}

    >>> parse_match("A {:w} cat", "A blue and red cat")
    None

Use variables.

    >>> parse_match("{x:d}", "1")
    {'x': 1}

    >>> parse_match("A {desc} cat", "A blue cat")
    {'desc': 'blue'}

    >>> parse_match("A {desc} cat", "A blue and red cat")
    {'desc': 'blue and red'}

Groktest match support can be customized with custom match types.

    >>> parse_match(
    ...     "A {:color} cat",
    ...     "A blue cat",
    ...     types={"color": "blue|red"}
    ... )
    {}

    >>> parse_match(
    ...     "A {color:color} cat",
    ...     "A red cat",
    ...     types={"color": "blue|red"}
    ... )
    {'color': 'red'}

    >>> parse_match(
    ...     "A {:color} cat",
    ...     "A green cat",
    ...     types={"color": "blue|red"}
    ... )
    None

By default matches are case sensitive.

    >>> parse_match("Hello", "hello")
    None

Compare with case insensitive.

    >>> parse_match("Hello", "hello", options={"case": False})
    {}

Match types can specify a case-insensitive pattern using `(?i)`.

    >>> parse_match(
    ...     "A {color:color} cat",
    ...     "A RED cat",
    ...     types={"color": "(?i)blue|red"}
    ... )
    {'color': 'RED'}

    >>> parse_match(
    ...     "A {color:color} cat",
    ...     "A bluE cat",
    ...     types={"color": "(?i)blue|red"}
    ... )
    {'color': 'bluE'}

Patterns match across multipe lines.

    >>> parse_match(
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
    ... )
    {'stack': 'File "<stdin>", line 1, in <module>\n'
              'File "<stdin>", line 2, in boom'}

Non-patterns are sensitive to line-endings.

    >>> parse_match("a b", "a\nb")
    None

    >>> parse_match("a b", "\na b\n")
    None

To match the previous example, the leading and trailing line-endings
need to be stripped.

    >>> parse_match("a b", "\na b\n".strip())
    {}
