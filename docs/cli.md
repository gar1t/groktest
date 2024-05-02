# Groktest CLI

Run Groktest using the `groktest` command.

    >>> run("groktest --help")  # +diff
    usage: groktest [--version] [-h] [--preview] [--last] [-F] [--debug]
                    [[PROJECT [SUITE]] | [FILE...] ...]
    ⤶
    positional arguments:
      [PROJECT [SUITE]] | [FILE...]
                            Project suite or files to test.
    ⤶
    options:
      --version             Show version and exit.
      -h, --help            Show this help message and exit.
      --preview             Show tests without running them.
      --last                Re-run last tests.
      -F, --failfast        Stop on the first error for a file.
      --debug               Show debug info.
    ⤶
    <0>
