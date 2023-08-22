# SPDX-License-Identifier: Apache-2.0

from typing import *

import argparse
import glob
import json
import logging
import os
import tempfile

from .__init__ import test_file

from . import _vendor_tomli as toml

# Defer init to `_init_logging()`
log: logging.Logger = cast(logging.Logger, None)


ProjectData = Dict[str, Any]


class CmdConfig:
    def __init__(self, filenames: List[str]):
        self.filenames = filenames


def main():
    p = _init_parser()
    args = p.parse_args()

    _init_logging(args)

    _apply_last(args)

    config = _cmd_config(args)

    _maybe_save_last(args)

    failed = tested = 0

    for filename in config.filenames:
        if args.preview:
            print(f"Testing {filename} (preview)")
            continue
        print(f"Testing {filename}")
        try:
            result = test_file(filename)
        except FileNotFoundError:
            print(f"WARNING: {filename} does not exist, skipping")
        else:
            failed += result["failed"]
            tested += result["tested"]

    assert failed <= tested, (failed, tested)
    if tested == 0:
        print("Nothing tested 😴")
    elif failed == 0:
        print("All tests passed 🎉")
    else:
        print("Tests failed 💥 (see above for details)")


def _init_logging(args: Any):
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(levelname)s: [%(name)s] %(message)s",
    )
    globals()["log"] = logging.getLogger("groktest")


def _init_parser():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument(
        "paths",
        metavar="[PROJECT [SUITE]] | [FILE...]",
        type=str,
        help="Project suite or files to test.",
        nargs="*",
    )
    p.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit.",
    )
    p.add_argument(
        "--preview",
        action="store_true",
        help="Show tests without running them.",
    )
    p.add_argument("--last", action="store_true", help="Re-run last tests.")
    p.add_argument("--debug", action="store_true", help="Show debug info.")
    return p


def _apply_last(args: Any):
    if args.last:
        last = _last_paths()
        assert last
        args.paths = last


def _last_paths():
    paths = _read_last_paths()
    if not paths:
        raise SystemExit("Run at least one test before using --last")
    return paths


def _read_last_paths():
    try:
        f = open(_last_paths_savefile())
    except FileNotFoundError:
        return None
    else:
        with f:
            return json.load(f)


def _last_paths_savefile():
    return os.path.join(tempfile.gettempdir(), "groktest.last")


def _maybe_save_last(args: Any):
    if not args.last:
        with open(_last_paths_savefile(), "w") as f:
            json.dump(args.paths, f)


def _cmd_config(args: Any):
    return _try_project_config(args) or _default_config(args)


def _try_project_config(args: Any):
    if not args.paths:
        return None
    project_data = _try_project_data(args.paths[0])
    if not project_data:
        return None
    return _cmd_config_for_project_data(project_data, args)


def _try_project_data(path: str):
    candidates = [path, os.path.join(path, "pyproject.toml")]
    for filename in [path for path in candidates if os.path.isfile(path)]:
        try:
            return _load_toml(filename)
        except FileNotFoundError:
            pass
        except TypeError:
            pass
    return None


def _load_toml(filename: str):
    try:
        f = open(filename, "rb")
    except FileNotFoundError:
        raise
    with f:
        try:
            data = toml.load(f)
        except toml.TOMLDecodeError as e:
            raise TypeError from e
        else:
            log.debug("using project config in %s", filename)
            data["__filename__"] = filename
            return data


def _cmd_config_for_project_data(data: Dict[str, Any], any: Any):
    try:
        groktest_data = data["tool"]["groktest"]
    except KeyError:
        return None
    else:
        return _config_for_groktest_data(groktest_data, data["__filename__"])


def _config_for_groktest_data(data: Dict[str, Any], config_filename: str):
    try:
        include = _coerce_list(data["include"])
    except KeyError:
        raise SystemExit(
            f"Missing 'include' in 'tool.groktest' section in {config_filename}"
        )
    else:
        filenames = _filenames_for_test_patterns(
            include, _coerce_list(data.get("exclude"))
        )
        return CmdConfig(filenames)


def _coerce_list(val: Any) -> List[Any]:
    if isinstance(val, list):
        return val
    if val is None:
        return []
    return [val]


def _filenames_for_test_patterns(include: List[str], exclude: List[str]):
    excluded = set(_apply_test_patterns(exclude or [], "exclude"))
    included = _apply_test_patterns(include, "include")
    return [path for path in included if path not in excluded]


def _apply_test_patterns(patterns: List[str], desc: str):
    filenames: List[str] = []
    for pattern in patterns:
        matches = glob.glob(pattern, recursive=True)
        log.debug("tests for {desc} pattern '%s': %s", pattern, matches)
        filenames.extend(matches)
    return filenames


def _default_config(args: Any):
    return CmdConfig(args.paths)


if __name__ == "__main__":
    main()
