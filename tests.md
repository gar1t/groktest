---
test-format: doctest
---

# Groktest

## User API

    >>> import groktest as gkt

TODO

## Customizer API

A *customizer* is someone who customizes Groktest to provide new or
modified behavior.

- Languages
- Pattern match schemes
- Pattern features

TODO

## Internal API

The tests in this section demonstrate internal Groktest behavior. These
may be considered unit tests.

### Parsing front matter

The private function `_parse_front_matter()` parses front matter
specified in a string. Front matter is denoted by a line `---` at the
start of the file followed by a subseuqnet line `---`.

    >>> parsefm = gkt._parse_front_matter

    >>> parsefm("")
    {}

### Runner state

TODO

Runner state an internal construct Groktest uses when running tests.

    >> state = gkt.init_runner_state("examples/doctest.md")

Groktest loads the specified file and initializes runner state.

TODO

#### Errors

A file must exist.

    >>> gkt.init_runner_state("does_not_exist")
    Traceback (most recent call last):
    FileNotFoundError: [Errno 2] No such file or directory: 'does_not_exist'
