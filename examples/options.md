---
test-options: +wildcard +blankline=.
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

    >>> "Wildcard matching is enabled"  # +wildcard="< >"
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
