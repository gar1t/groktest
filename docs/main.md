# Groktest main

The main CLI interface is defined in `groktest.__main__`.

    >>> from groktest.__main__ import main

Create a function to run Groktest using the main function.

    >>> def run_main(args):
    ...     import subprocess
    ...     cmd = ["python", "-m", "groktest.__main__", *args]
    ...     try:
    ...         out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
    ...     except subprocess.CalledProcessError as e:
    ...         print(e.output)
    ...         print(f"<exit {e.returncode}>")
    ...     else:
    ...         print(out, end="")

Create some files to test.

    >>> import tempfile, os

    >>> tmp = tempfile.mkdtemp(prefix="groktest-")

Passing test:

    >>> test_pass = os.path.join(tmp, "pass.md")
    >>> _ = open(test_pass, "w").write("""
    ... >>> 1
    ... 1
    ... """)

Failing test:

    >>> test_fail = os.path.join(tmp, "fail.md")
    >>> _ = open(test_fail, "w").write("""
    ... >>> 1
    ... 2
    ... """)

No tests:

    >>> test_empty = os.path.join(tmp, "empty.md")
    >>> _ = open(test_empty, "w").close()

Run the tests.

    >>> run_main([test_pass])  # +wildcard +paths
    Testing .../pass.md
    ----------------------------------------------------------------------
    1 test run
    All tests passed 🎉

    >>> run_main([test_fail])  # +wildcard +paths
    Testing .../fail.md
    **********************************************************************
    File ".../fail.md", line 2
    Failed example:
        1
    Expected:
        2
    Got:
        1
    ----------------------------------------------------------------------
    1 test run
    1 test failed in 1 file 💥 (see above for details)
     - .../fail.md
    ⤶
    <exit 1>

    >>> run_main([test_empty])  # +wildcard +paths
    Testing .../empty.md
    ----------------------------------------------------------------------
    Nothing tested 😴
    ⤶
    <exit 2>

## Version

Groktest version is defined in two locations: `pyproject.toml` and in
the `groktest` module. The duplication eliminates the complexity of
sharing a single definition but adds the need to manually synchronize
the values.

This test checks that they are the same.

    >>> import groktest, os
    >>> import groktest._vendor_tomli as tomli

    >>> config_src = os.path.join(
    ...     os.path.dirname(os.path.dirname(groktest.__file__)),
    ...     "pyproject.toml")
    >>> config = tomli.load(open(config_src, "rb"))

    >>> project_ver = config["project"]["version"]
    >>> src_ver = groktest.__version__

    >>> assert src_ver == project_ver
