---
test-type: doctest
---

# Matching test result output and expected

## Parse matching

Grokville's `parse` option enables parse matching. Parse matching is
implemented by `groktest._ParseMatcher`.

    >>> from groktest import _ParseMatcher

Create a function to test parse matching.

    >>> def parse_match(
    ...     expected,
    ...     test_output,
    ...     types=None,
    ...     case_sensitive=True,
    ... ):
    ...     matcher = _ParseMatcher(types, case_sensitive)
    ...     match = matcher(expected, test_output)
    ...     if match:
    ...         pprint(match.bound_variables)
    ...     else:
    ...         print("<no match>")

Match simple output.

    >>> parse_match("1", "1")
    {}

Use format expressions.

    >>> parse_match("{}", "1")
    {}

    >>> parse_match("{:d}", "1")
    {}

    >>> parse_match("{:D}", "1")
    <no match>

    >>> parse_match("A {} cat", "A blue cat")
    {}

    >>> parse_match("A {} cat", "A red cat")
    {}

    >>> parse_match("A {} cat", "A red dog")
    <no match>

    >>> parse_match("A {} cat", "A blue and red cat")
    {}

    >>> parse_match("A {:w} cat", "A blue and red cat")
    <no match>

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
    ...     {"color": "blue|red"}
    ... )
    {}

    >>> parse_match(
    ...     "A {color:color} cat",
    ...     "A red cat",
    ...     {"color": "blue|red"}
    ... )
    {'color': 'red'}

    >>> parse_match(
    ...     "A {:color} cat",
    ...     "A green cat",
    ...     {"color": "blue|red"}
    ... )
    <no match>

By default matches are case sensitive.

    >>> parse_match("Hello", "hello")
    <no match>

Compare with case insensitive.

    >>> parse_match("Hello", "hello", case_sensitive=False)
    {}

Match types can specify a case-insensitive pattern using `(?i)`.

    >>> parse_match(
    ...     "A {color:color} cat",
    ...     "A RED cat",
    ...     {"color": "(?i)blue|red"},
    ...     case_sensitive=True
    ... )
    {'color': 'RED'}

    >>> parse_match(
    ...     "A {color:color} cat",
    ...     "A bluE cat",
    ...     {"color": "(?i)blue|red"},
    ...     case_sensitive=True
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
    <no match>

    >>> parse_match("a b", "\na b\n")
    <no match>

To match the previous example, the leading and trailing line-endings
need to be stripped.

    >>> parse_match("a b", "\na b\n".strip())
    {}
