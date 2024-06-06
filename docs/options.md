# Test options

Test options are flags used to control test behavior. An option may be
enabled or disabled, When enabled, an option may have a value.

## Supported options

- `parse`

   Output is matched using the `parse` library. Disabled by default.

   Enable this option to specify output type or to capture output to
   variables.

- `case`

  Output matching is case-sensitive. Enabled by default.

  Disable for case-insensitive matches using `-case`.

- `skip`

  Skips a test. Disabled by default.

  All tests in a test file can be skipped by enabling this option in
  front-matter. Individual tests can be unskipped using `-skip` in this
  case.

- `skiprest`

  Skips current and following tests. Disabled by default.

  Subsequent tests can be unskipped using `-skip`. Similarly, `skiprest`
  can be disabled using `-skiptest`.

- `fails`

  Indicates that the test is expected to fail. Disabled by default.

  It can be useful to include tests that fail as examples. If the test
  succeeds unexpectedly, the success is recorded as a failure in the
  output. Otherwise the test is considered to have passed.

  Similar in application to `+skip` but asserts an expected failure.

- `solo`

  Run only tests enabled for solo, if any are enabled. Defaults to
  disabled.

  Soloing one or more tests is an easy way to run only certain tests.
  This is useful when debugging a failing test.

- `blankline`

  A value specified the blank line marker. Default is config specific.

  E.g. `+blankline=<BLANKLINE>` set the `doctest` marker.

  Use `-blankline` to prevent use of blank lines in examples.

- `wildcard`

  Match any output using a wildcard token. Disabled by default. Accepts
  an optional value when enabled.

  When enabled the configured wildcard will match any characters up
  until the output following the wildcard token.

  The default wildcard token is `...` when this option is enabled.

  The wildcard can be configured for all tests in a test file using the
  file front matter.

- `space`

  Consider whitespace when comparing expected and test output. Enabled
  by default.

  To disregard whitespace in matches, disable the option using
  `-space`.

- `paths`

  Normalize paths to be `/` or `\`. Defaults to disabled and `/` if
  enabled without an explicit value.

- `pprint`

  Test output is formatted using "pretty print" when enabled. Disabled
  by default.

  Runtimes supported: Python

- `stderr`

  Capture standard error as well as standard output in the expected
  output.

## Custom options

Use `option-functions` to specify one or more modules that define option
functions.

An option function is named starting with `option_`. By default, the
option name is inferred from the function name. `option_xxx` for
example, defines the option `xxx`.

The function can provide an `option_name` attribute to specify the
option name.

`example/custom-options.md` illustrates how custom options are defined
and used.

## Implementation notes

### Parsing options

Groktest uses the private function `_parse_config_options`.

    >>> def parse(options):
    ...     from pprint import pprint
    ...     from groktest import _test_options_for_config
    ...     pprint(_test_options_for_config({"options": options}, "<test>"))

Options are specified using `+<name>` and `-<name>` to enable and
disable an option respectively.

    >>> parse("+foo")
    {'foo': True}

    >>> parse("-bar")
    {'bar': False}

    >>> parse("+foo -bar")
    {'bar': False, 'foo': True}

    >>> parse("-bar +foo")
    {'bar': False, 'foo': True}

If an option is specified more than once, the last occurrence is used to
determine the option value.

    >>> parse("-foo +foo")
    {'foo': True}

    >>> parse("+foo -foo")
    {'foo': False}

If an enabled option has a value, it is specified using `+<name>=<value>`.

    >>> parse("+foo=123")
    {'foo': 123}

Spaces may appear before or after the equals sign.

    >>> parse("+foo = 123")
    {'foo': 123}

A Value may be quoted using single or double quotes.

    >>> parse("+foo = '123'")
    {'foo': '123'}

    >>> parse("+foo = \"123\"")
    {'foo': '123'}

    >>> parse("+foo = \"a value with spaces\"")
    {'foo': 'a value with spaces'}

    >>> parse("+foo = 'also with spaces'")
    {'foo': 'also with spaces'}

If quotes aren't balanced, the first token after the equals space is
used as the value.

    >>> parse("+foo = 'not balanced")
    {'foo': "'not"}

    >>> parse("+foo = not balanced'")
    {'foo': 'not'}

This syntax is not supported with negation.

    >>> parse("-foo=123")
    {'foo': False}

Tokens that don't match the option specification are ignored.

    >>> parse("Nothing here is an option")
    {}

    >>> parse("")
    {}

    >>> parse("+ foo")
    {}

    >>> parse("foo=123")
    {}

Typical configuration examples:

    >>> parse("+wildcard")
    {'wildcard': True}

    >>> parse("-case")
    {'case': False}

    >>> parse("+wildcard -case")
    {'case': False, 'wildcard': True}

    >>> parse("+wildcard=* -space")
    {'space': False, 'wildcard': '*'}

### Decoding Options

`decode_options` decodes an option string to a dict of option values.

    >>> from groktest import decode_options

    >>> decode_options("+foo")
    {'foo': True}

    >>> decode_options("+foo=123")
    {'foo': 123}

    >>> decode_options("+foo=abc")
    {'foo': 'abc'}

    >>> decode_options("-foo")
    {'foo': False}

    >>> decode_options("+foo +bar")  # +pprint
    {'bar': True, 'foo': True}

    >>> decode_options("+foo=123 -bar")  # +pprint
    {'bar': False, 'foo': 123}

    >>> decode_options("+foo=abc bar")
    {'foo': 'abc'}

    >>> decode_options("""
    ...   +foo this text is ignored
    ...   +bar=123
    ... """)  # +pprint
    {'bar': 123, 'foo': True}
