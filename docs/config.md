# Config

Test configuration can be specified in various ways.

- Project config
- Test file front matter
- CLI options (limited)

The scheme is complicated by the fact that the CLI uses project
configuration to convey settings to tests. This introduces two project
level config: one implicitly defined by the CLI and another inferred
when running a test file.

The function `groktest._test_config` implements this logic. It merges
three config source: base project config (from a possible project and
possible CLI generated config), a test file project config (inferred by
the test file's location relative to a project file) and test front
matter.


    >>> run("groktest examples/config/test.md --debug --fail-fast")  # +parse
    {}
    DEBUG: [groktest] Test config: {config}
    {}
    Testing examples/config/test.md
    ----------------------------------------------------------------------
    1 test run
    All tests passed 🎉
    ⤶
    <0>

    >>> pprint(eval(config))  # +wildcard +paths
    {'__src__': ['.../examples/config/test.md',
                 '.../examples/config/pyproject.toml'],
     'fail-fast': True,
     'options': ['-wildcard', '+wildcard']}
