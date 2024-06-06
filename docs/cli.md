# Groktest CLI

Run Groktest using the `groktest` command.

    >>> run("groktest --help")  # +diff
    usage: groktest [--version] [-h] [--preview] [--last] [-f] [-C N]
                    [--show-skipped] [--debug]
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
      -f, --fail-fast       Stop on the first error for a file.
      -C N, --concurrency N
                            Max number of concurrent tests.
      --show-skipped        Show skipped tests in output.
      --debug               Show debug info.
    ⤶
    <0>

    >>> run("groktest --version")
    Groktest 0.2.2
    ⤶
    <0>
