---
test-type: nushell
---

The last expression is evaluated.

    > 1 + 1
    2

    > 1 + 1; 2 + 2
    4

Test starts in the test doc directory.

    > $env.PWD  # +wildcard +paths
    .../examples

    > ls *.md | get name | to text  # +wildcard
    assert.md
    defaults.md
    ...
    whitespace.md

Nushell tests are configured with a temporary directory, which can be
referenced using `$env.TEST_TEMP`.

    > $env.TEST_TEMP  # +wildcard +paths
    .../groktest-nushell-...

    > cd $env.TEST_TEMP

    > $env.PWD  # +wildcard +paths
    .../groktest-nushell-...

    > ls

    > touch hello

    > ls
    name  type size modified
    hello file  0 B now

Bound variables are accessible via the `vars` Nu variable.

    > print "Hello Joe"  # +parse
    Hello {name}

    > $vars.name
    Joe

Other variables are NOT retained across tests.

    > let x = 123

    > $x
    Error: nu::parser::variable_not_found
