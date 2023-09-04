# SPDX-License-Identifier: Apache-2.0

from typing import *

from .__init__ import ProjectConfig

import argparse
import glob
import json
import logging
import os
import tempfile

from .__init__ import test_file
from .__init__ import load_project_config
from .__init__ import ProjectDecodeError
from .__init__ import TestTypeNotSupported

# Defer init to `_init_logging()`
log: logging.Logger = cast(logging.Logger, None)


def main():
    p = _init_parser()
    args = p.parse_args()

    _init_logging(args)

    _apply_last(args)

    config = _try_project_config(args)

    failed = tested = 0

    for filename in _test_filenames(config, args):
        relname = os.path.relpath(filename)
        if args.preview:
            print(f"Testing {relname} (preview)")
            continue
        print(f"Testing {relname}")
        try:
            result = test_file(filename, config)
        except FileNotFoundError:
            log.warning("%s does not exist, skipping", filename)
        except IsADirectoryError:
            log.warning("%s is a directory, skipping", filename)
        except TestTypeNotSupported as e:
            log.warning("Test type '%s' for %s is not supported, skipping", e, filename)
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
    from .__init__ import __name__

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
        args.paths = _last_paths()
    else:
        _save_last_cmd(args)


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


def _save_last_cmd(args: Any):
    if not args.last:
        with open(_last_paths_savefile(), "w") as f:
            json.dump(args.paths, f)


def _try_project_config(args: Any):
    if not args.paths:
        return None
    project_path = _project_candidate(args.paths[0])
    if not project_path:
        return None
    try:
        config = load_project_config(project_path)
    except ProjectDecodeError as e:
        log.debug("Error loading project config from %s: %s", project_path, e)
    else:
        if len(args.paths) > 1:
            raise SystemExit(
                f"extra arguments '{' '.join(args.paths[1:])}' to project "
                "path not currently supported"
            )
        return config


def _project_candidate(path_arg: str):
    paths = [path_arg, os.path.join(path_arg, "pyproject.toml")]
    for path in paths:
        if path[-5:].lower() == ".toml" and os.path.isfile(path):
            return path
    return None


def _test_filenames(config: Optional[ProjectConfig], args: Any):
    if config is None:
        return args.paths
    include = _coerce_list(config.get("include"))
    if not include:
        raise SystemExit(f"Missing 'include' in 'tool.groktest' section in {config['__src__']}")
    basepath = os.path.dirname(config["__src__"])
    exclude = _coerce_list(config.get("exclude"))
    return _filenames_for_test_patterns(include, exclude, basepath)


def _coerce_list(val: Any) -> List[Any]:
    if isinstance(val, list):
        return val
    if val is None:
        return []
    return [val]


def _filenames_for_test_patterns(include: List[str], exclude: List[str], basepath: str):
    excluded = set(_apply_test_patterns(exclude or [], basepath, "exclude"))
    included = _apply_test_patterns(include, basepath, "include")
    return [path for path in included if path not in excluded]


def _apply_test_patterns(patterns: List[str], basepath: str, desc: str):
    filenames: List[str] = []
    for pattern in patterns:
        pattern_path = os.path.join(basepath, pattern)
        matches = glob.glob(pattern_path, recursive=True)
        log.debug("tests for %s pattern '%s': %s", desc, pattern, matches)
        filenames.extend([os.path.normpath(path) for path in matches])
    return filenames


if __name__ == "__main__":
    main()
