# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import *

import logging
import os
import re
import subprocess
import tempfile
import textwrap

from .__init__ import Runtime
from .__init__ import Test
from .__init__ import TestConfig
from .__init__ import TestMatch
from .__init__ import TestOptions
from .__init__ import TestResult

log = logging.getLogger("groktest.python")

_ENV_VAR_NAME_P = re.compile(r"^[A-Z][A-Z0-9_-]*$")

_CONFIG_TEMPLATE = """
$env.config = {
    show_banner: false
    ls: {
        use_ls_colors: false
        clickable_links: false
    }
    table: {
        mode: none
        index_mode: auto
        show_empty: false
        padding: { left: 0, right: 0 }
        trim: {
            methodology: wrapping
            wrapping_try_keep_words: true
        }
    }
    color_config: {}
    footer_mode: never
    use_ansi_coloring: false
}
"""


class NuShellRuntime(Runtime):
    _cache: Optional[Dict[str, Any]] = None

    def start(self, config: Optional[TestConfig] = None):
        self._cache = {}

    def init_for_tests(self, config: TestConfig | None = None) -> None:
        assert self._cache is not None
        self._cache = _init_tests()

    def exec_test_expr(self, test: Test, options: TestOptions):
        assert self._cache is not None
        _maybe_apply_test_cwd(test, self._cache)
        return _exec_test_expr(test, self._cache)

    def handle_test_match(self, match: TestMatch):
        if match.match and match.vars:
            assert self._cache is not None
            self._cache.update(match.vars)

    def stop(self, timeout: int = 5):
        self._cache = None

    def is_available(self):
        return self._cache is not None


def _init_tests():
    return {
        "TEMP": tempfile.gettempdir(),
        "TEST_TEMP": tempfile.mkdtemp(prefix="groktest-nushell-"),
        "__cfg__": _write_test_config(),
    }


def _write_test_config():
    dir = tempfile.mkdtemp(prefix="groktest-nushell-")
    filename = os.path.join(dir, "config.nu")
    with open(filename, "w") as f:
        f.write(_CONFIG_TEMPLATE)
    return filename


def _maybe_apply_test_cwd(test: Test, cache: Dict[str, Any]):
    cache.setdefault("__cwd__", os.path.dirname(test.filename))


def _exec_test_expr(test: Test, cache: Dict[str, Any]):
    cmd = _test_cmd(test.expr)
    cwd = _test_cwd(cache)
    env = _test_env(cache)
    _log_command(cmd, cwd, env)
    cfg = cache["__cfg__"]
    p = _open_nu_proc(cmd, cwd, env, cfg)
    out, err = p.communicate()
    _log_output(out)
    result_output, cwd = _parse_output(out)
    cache["__cwd__"] = cwd
    return TestResult(p.returncode, result_output)


def _test_cmd(expr: str):
    return f"print (\n{expr}\n); pwd"


def _test_env(cache: Dict[str, Any]) -> Dict[str, str]:
    return {name: cache[name] for name in cache if _env_var_name(name)}


def _env_var_name(s: str):
    return _ENV_VAR_NAME_P.match(s)


def _test_cwd(cache: Dict[str, Any]) -> Optional[str]:
    return cache["__cwd__"]


def _log_command(cmd: str, cwd: Optional[str], env: Dict[str, str]):
    if log.getEffectiveLevel() > logging.DEBUG:
        return
    log.debug("Running Nu command:")
    log.debug(textwrap.indent(f"cmd: {cmd}", "  "))
    log.debug(textwrap.indent(f"cwd: {cwd}", "  "))
    log.debug(textwrap.indent(f"env: {env}", "  "))


def _log_output(output: str):
    log.debug(textwrap.indent(f"out: {output!r}", "  "))


def _open_nu_proc(cmd: str, cwd: Optional[str], env: Dict[str, str], cfg: str):
    try:
        return subprocess.Popen(
            ["nu", "--config", cfg, "-c", cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            env={**os.environ, **env},
            text=True,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "cannot find 'nu' program\n"
            "Confirm that Nushell is installed and available on the path"
        ) from None


def _parse_output(output: str):
    parts = output.rsplit("\n", 2)
    if parts[-1] != "":
        raise AssertionError(repr(output))
    if len(parts) == 2:
        return "", parts[0]
    if len(parts) == 3:
        return parts[0] + "\n", parts[1]
    raise AssertionError(repr(output))
