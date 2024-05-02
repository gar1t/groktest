# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import *

import json
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

log = logging.getLogger(__name__)

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


class State:
    def __init__(self, config_home: str):
        self.config_home = config_home
        self.test_dir: Optional[str] = None
        self.vars: Dict[str, Any] = {}
        self.last_saved_vars = None
        self.env: Dict[str, str] = {}
        self.cwd: Optional[str] = None
        self.config: Optional[TestConfig] = None

    @property
    def test_config_filename(self):
        return os.path.join(self.config_home, "config.nu")

    @property
    def vars_json_filename(self):
        return os.path.join(self.config_home, "vars.json")

    @property
    def vars_nu_filename(self):
        return os.path.join(self.config_home, "vars.nu")


class NuShellRuntime(Runtime):
    _state: Optional[State] = None

    def start(self, config: Optional[TestConfig] = None):
        self._state = _init_state()

    def init_for_tests(self, config: Optional[TestConfig] = None) -> None:
        assert self._state is not None
        self._state.vars.clear()
        self._state.cwd = None
        self._state.config = config

    def exec_test_expr(self, test: Test, options: TestOptions):
        assert self._state
        _apply_test_cwd(test, self._state)
        _apply_vars(self._state)
        return _exec_test_expr(test, self._state)

    def handle_test_match(self, match: TestMatch):
        if match.match and match.vars:
            assert self._state
            self._state.vars.update(match.vars)

    def stop(self, timeout: int = 5):
        self._cache = None

    def is_available(self):
        return self._cache is not None


def _init_state():
    state = State(tempfile.mkdtemp(prefix="groktest-nushell-"))
    _write_test_config(state)
    state.env = {
        "TEMP": tempfile.gettempdir(),
        "TEST_TEMP": tempfile.mkdtemp(prefix="groktest-nushell-"),
    }
    return state


def _write_test_config(state: State):
    with open(state.test_config_filename, "w") as f:
        f.write(_CONFIG_TEMPLATE)


def _apply_test_cwd(test: Test, state: State):
    if not state.test_dir:
        state.test_dir = os.path.dirname(test.filename)


def _apply_vars(state: State):
    if state.last_saved_vars != state.vars:
        _write_vars_json(state)
        _generate_vars_mu(state)


def _write_vars_json(state: State):
    with open(state.vars_json_filename, "w") as f:
        json.dump(state.vars, f)


def _generate_vars_mu(state: State):
    assert os.path.exists(state.vars_json_filename)
    cmd = ["nu", "--commands", _format_mu_vars_source_command(state)]
    subprocess.check_call(cmd)


def _format_mu_vars_source_command(state: State):
    return f"""
    $"mut vars = (
        open --raw {state.vars_json_filename}
        | from json | to nuon
    )" | save -f {state.vars_nu_filename}
    """


def _exec_test_expr(test: Test, state: State):
    assert state.test_dir
    assert os.path.exists(state.vars_nu_filename)
    cmd = [
        "nu",
        "--config",
        state.test_config_filename,
        "--commands",
        _format_nu_test_expr_command(test, state),
    ]
    cwd = state.test_dir
    env = state.env
    _log_command(cmd, cwd, env)
    try:
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            env={**os.environ, **state.env},
            text=True,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "cannot find 'nu' program\n"
            "Confirm that Nushell is installed and available on the path"
        ) from None
    else:
        out, err = p.communicate()
        _log_output(out)
        result_output, cwd = _parse_output(out)
        state.cwd = cwd
        return TestResult(
            p.returncode,
            result_output,
            _maybe_short_error(p.returncode, result_output),
        )


def _maybe_short_error(code: int, output: str):
    if code != 0 and output.startswith("Error: "):
        return output.split("\n", 1)[0] + "\n"
    return None


def _format_nu_test_expr_command(test: Test, state: State):
    return f"""
    {_init_commands(state)}
    {_source_vars_command(state)}
    {_cd_command(state)}
    print (
        {test.expr}
    )
    $env.PWD
    """


def _init_commands(state: State):
    if not state.config:
        return ""
    try:
        return state.config["nushell"]["init"]
    except KeyError:
        return ""


def _source_vars_command(state: State):
    return f"source {state.vars_nu_filename}"


def _cd_command(state: State):
    if not state.cwd:
        return ""
    return f"cd `{state.cwd}`"


def _log_command(cmd: List[str], cwd: str, env: Dict[str, str]):
    if log.getEffectiveLevel() > logging.DEBUG:
        return
    log.debug("Running Nu command:")
    log.debug(textwrap.indent(f"cmd: {cmd}", "  "))
    log.debug(textwrap.indent(f"cwd: {cwd}", "  "))
    log.debug(textwrap.indent(f"env: {env}", "  "))


def _log_output(output: str):
    log.debug(textwrap.indent(f"out: {output!r}", "  "))


def _parse_output(output: str):
    parts = output.rsplit("\n", 2)
    if parts[-1] != "":
        raise AssertionError(repr(output))
    if len(parts) == 2:
        return "", parts[0]
    if len(parts) == 3:
        return _strip_line_padding(parts[0]) + "\n", parts[1]
    raise AssertionError(repr(output))


def _strip_line_padding(s: str):
    return "\n".join(line.rstrip() for line in s.split("\n"))
