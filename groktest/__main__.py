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


class CmdConfig:
    def __init__(self, filenames: List[str]):
        self.filenames = filenames


def main():
    p = _init_parser()
    args = p.parse_args()

    _init_logging(args)

    config = _config_for_args(args)

    if not args.last:
        # Call only after `_config_for_args()`
        _save_last_paths(args.paths)

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


def _config_for_args(args: Any):
    paths = (args.last and _last_paths()) or args.paths
    config = _project_config(paths) or CmdConfig(paths)
    _apply_args_to_config(args, config)
    return config


def _filenames_for_args(args: Any):
    if args.last:
        if args.paths:
            raise SystemExit(
                "Cannot specify both PATH and --last\n"  # \
                "Try 'groktest -h' for help."
            )
        return _last_paths()
    else:
        if not args.paths:
            raise SystemExit(
                "Nothing to test (expected PATH or --last)\n"  # \
                "Try 'groktest -h' for help."
            )
        return args.paths


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


def _project_config(paths: List[str]):
    if paths:
        project_config = _try_load_toml(paths[0])
        if project_config:
            if len(paths) > 1:
                raise SystemExit(
                    f"Groktest does not yet support SUITE args ('{paths[1]}')"
                )
            return _config_for_project_data(project_config)
    return None


def _try_load_toml(path: str):
    candidates = [path, os.path.join(path, "pyproject.toml")]
    for filename in [path for path in candidates if os.path.isfile(path)]:
        data = _try_load_toml_(filename)
        if data:
            return data
    return None


def _try_load_toml_(filename: str):
    try:
        f = open(filename, "rb")
    except FileNotFoundError:
        return None
    with f:
        try:
            data = toml.load(f)
        except toml.TOMLDecodeError:
            return None
        else:
            log.debug("using project config in %s", filename)
            data["__filename__"] = filename
            return data


def _config_for_project_data(data: Dict[str, Any]):
    try:
        groktest_data = data["tool"]["groktest"]
    except KeyError:
        return None
    else:
        return _config_for_groktest_data(groktest_data, data["__filename__"])


def _config_for_groktest_data(data: Dict[str, Any], config_filename: str):
    try:
        include = data["include"]
    except KeyError:
        raise SystemExit(
            f"Missing 'include' in 'tool.groktest' section in {config_filename}"
        )
    else:
        filenames = _filenames_for_test_patterns(include, data.get("exclude"))
        return CmdConfig(filenames)


def _filenames_for_test_patterns(
    include: List[str], exclude: Optional[List[str]] = None
):
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


def _apply_args_to_config(args: Any, config: CmdConfig):
    # TODO: apply applicable args to config as overrides
    pass


def _loglevel_for_args(args: Any):
    return logging.DEBUG if args.debug else logging.WARNING


def _save_last_paths(filenames: List[str]):
    with open(_last_paths_savefile(), "w") as f:
        json.dump(filenames, f)


if __name__ == "__main__":
    main()
