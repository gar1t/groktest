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
its kind. We owe a debt of grattutude to Tim Peters for the original
work and to Jim Fulton for advancing its use.

The rationale for `doctest` is that examples provide a high-signal,
low-noise representation of developer intent.

- Tests are framed within comments (rather than using comments), which
  encourages a narrative mode of testing
- Examples are often easier to understand (grok) than a series of
  assertions
- Example output can replace a large number of explicit assertions,
  providing more test coverage with fewer expresions

`doctest` however presents some key problems.

- Result comparison can use an ellipsis `...` to match any output; while
  the match is geedy, it can match invalid output and mast errors
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

The simplest example is a

    > 'The number 42 is overused in examples'
    'The number 42 is overused in examples'

In `groktest` you can provide an assertion expression.


    > 'The number 42 is overused in examples'
    'The number {\ugh} is overused in examples'

What about a more complex assertion?

    > 'The number 42 is overused in examples'
    'The number {(?<x>\d+); {x >= 42} is overused in examples'

Binding output to an assertion variable:

    > 'foo is 123'
    'foo is {(?<foo>\d+)}'

    > 'bar is also 123'
    bar is also {\k<foo>}

Match anything:

    > 'The sun will eventually run out of fuel lol'
    The sun will eventually {.*}

Match digits.

    > '1 + 1 is 2'
    {\d+} + {\d+} is {\d+}

## Contributing

Please feel free to reach out if you'd like to contribute to this
project. While we don't have a contribution policy we will get there! In
the meantime, use the following guidelines:

1. Use the [project issue
   tracker](https://github.com/gar1t/groktest/issues) to ask questions,
   report bugs, and suggest features.

2. Contributions will be accepted via pull requests.

3. All source code is formatted using `black` - expect any contribution
   to be reformatted on this basis.

4. Before working on a contribution, we recommend opening an issue to
   get early feedback.

5. We expect contributors to follow generally accepted standards of
   respect and kindness to others.
