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

    > ls

Changes to the directory are reflected across tests.

    > cd $env.TEST_TEMP

    > $env.PWD  # +wildcard +paths
    .../groktest-nushell-...

    > ls
    ⤶
