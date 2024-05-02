---
test-type: doctest
---

# Groktest

Groktest is a test framework that's inspired by Python's long standing
[`doctest`](https://docs.python.org/3/library/doctest.html) library.

Similarities to `doctest`:

- A test suite is a plain text file containing more or more tests
- A test is an *expression* accompanied by an *expected result*
- A test is run by evaluating the expression in the applicable
  language environment to generate a *computed result*
- A test passes when its *computed result* matches is *expected result*
  and fails otherwise

Differences to `doctest`:

- Test expressions may be defined in any supported language (currently
  Python, bash planned, support for other languages over time)
- Expected results may contain format-expressions, which are used to
  match expected output to a pattern with optional value capture to
  runtime state variables (see examples below)
- Tests are not sensitive to white-space by default
- Test options do not require a `doctest:` prefix
- Front-matter in test files may be used to configure a test suite

### Why?

Python's `doctest` paved the way for computational documents like
Jupyter Notebooks, R Markdown, and Quarto. It was one of the first of
its kind. We owe a debt of gratitude to Tim Peters for the original
work and to Jim Fulton for advancing its use.

The rationale for `doctest` is that examples provide a high-signal,
low-noise representation of developer intent.

- Tests are framed within comments (rather than using comments), which
  encourages a narrative mode of testing
- Examples are often easier to understand (grok) than a series of
  assertions
- Example output can replace a large number of explicit assertions,
  providing more test coverage with fewer expressions

`doctest` however presents some key problems.

- Result comparison can use an ellipsis `...` to match any output; while
  the match is greedy, it can match invalid output and mast errors
- The framework is Python specific and difficult to apply to cases
  outside Python
- Pattern matching is limited to a single 'match all' pattern
- Output from tests cannot be captured for use in subsequent tests

Groktest addresses these issues while maintaining the original `doctest`
value proposition.

### Not supported in Groktest

Groktest is in its early development phases. Its immediate goal is to be
a near drop-in replacement for `doctest` for tests defined in standalone
plain text files.

Groktest is not designed to test Python doc strings. Use `doctest` for
that.

While Groktest is designed to be language independent, it will take some
time to get this right. In order of priority, Groktest will support:

1. Tests defined using Python expressions (under development)
2. Tests defined as shell commands with bash/sh as the first target (planned)
3. Other runtimes as the project evolves (e.g R, Node, Julia, Erlang,
   etc.)

## Examples

The simplest example is an exact match.

    >>> 'The number 42 is overused in examples'
    'The number 42 is overused in examples'

In `groktest` you can provide a *format expression*, which has the
format `{[name][:format]}`. The following example asserts that the claim
contains a series of digits.

    >>> 'The number 42 is overused in examples'  # doctest: +SKIP
    'The number {:d} is overused in examples'

Matched values can be bound to local variables.

    >>> 'The number 42 is overused in examples'  # doctest: +SKIP
    'The number {n} is overused in examples'

    >>> n == 42  # doctest: +SKIP
    True

Output parsing is provided by Richard Jones' outstanding
[`parse`](https://github.com/r1chardj0n3s/parse) library.

To match anything, use `{}`.

    >>> 'Another tedious example is the use of "ham" and "spam"'
    ... # doctest: +SKIP
    'Another tedious example is {}'

Multiline expressions are continued on subsequent lines using `...`.

    >>> (1 +
    ... 2 + 4)
    7

Front matter is used to configure tests.

    ---
    test-config:
      ps1: '> '
      ps2: '+ '
    ---

    > "This should be familiar
    + to R developers"

Aside: In this case the use of `>` conflicts with Markdown's syntax for
block quotes. We recommend indenting tests with four spaces in Markdown
files.

Custom format types may be defined in test font matter.

    ---
    test-config:
      match-types:
        id: [a-f0-9]{8}
    ---

    >>> 'Sample id is abcd1234'  # doctest: +SKIP
    Sample id is {:id}

## What works?

A this point Groktest is in early development and nothing much of use is
available.

Refer to Groktest tests to see what works. Run them to verify!

    $ groktest *.md docs/*.md

## Contributing

Please feel free to reach out if you'd like to contribute to this
project. While we don't have a contribution policy we will get there! In
the meantime, use the following guidelines:

1. Use the [project issue
   tracker](https://github.com/gar1t/groktest/issues) to ask questions,
   report bugs, and suggest features.

2. Contributions will be accepted via pull requests.

3. All tests in [`tests.md`](tests.md) should pass.

4. All source code is formatted using `black` - expect any contribution
   to be reformatted on this basis.

5. Before working on a contribution, we recommend opening an issue to
   get early feedback.

6. We expect contributors to follow generally accepted standards of
   respect and kindness to others.
