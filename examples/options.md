---
test-options: +wildcard +blankline=. -case -space
---

Wildcard matching is enabled in front matter above.

    >>> "Wildcard matching is enabled"
    'Wild... matching...'

It can be disabled for specific tests.

    >>> "Wildcard matching is NOT enabled"  # -wildcard +fails
    'Wild... matching...'

The wildcard token can be modified for tests.

    >>> "Wildcard matching is enabled"  # +wildcard=**
    'Wild** matching**'

The token can contain spaces. Strange but true.

    >>> "Wildcard matching is enabled"  # Weird: +wildcard="< >"
    'Wild< > matching< >'

Blank lines are configured in front matter as periods.

    >>> print("")
    .

    >>> print("\n\n")
    .
    .
    .

A test example with blank line token will always fail.

    >>> print(".\n.\n.")  # +fails
    .
    .
    .

To work around this, use a different blank line token or disable the
option.

    >>> print(".\n.\n.")  # -blankline
    .
    .
    .

`case` is disabled in front matter. Test are case insensitive by
default.

    >>> print("X")
    x

Case sensitive matching can be enabled per test.

    >>> print("X")  # This test +fails because it's +case sensitive
    x

White space preservation is disabled by default in front matter.

    >>> print("""
    ... This spans
    ... some
    ... lines""")
    This spans some
    lines

It can be re-enabled per test.

    >>> print("""
    ... This spans
    ... some
    ... lines""")  # +space +fails
    This spans some
    lines
