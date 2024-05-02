# SPDX-License-Identifier: Apache-2.0

from typing import *

from .__init__ import ProjectConfig

import argparse
import glob
import json
import logging
import os
import sys
import tempfile

from .__init__ import __version__
from .__init__ import test_file
from .__init__ import load_project_config
from .__init__ import ProjectDecodeError
from .__init__ import TestTypeNotSupported

# Defer init to `_init_logging()`
log: logging.Logger = cast(logging.Logger, None)

EXIT_FAILED = 1
EXIT_NO_TESTS = 2


def main(args: Any = None):
    args = args or sys.argv[1:]
    p = _init_parser()
    args = p.parse_args(args)
    if args.version:
        _print_version_and_exit()

    _init_logging(args)
    _apply_last(args)
    config = _init_config(args)

    failed = tested = skipped = 0
    failed_files = []

    for filename in sorted(_test_filenames(config, args)):
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
            if result.failed:
                failed_files.append(filename)
            failed += result.failed
            tested += result.tested
            skipped += result.skipped

    assert failed <= tested, (failed, tested)
    _print_results(failed, tested, skipped, failed_files)


def _print_results(failed: int, tested: int, skipped: int, failed_files: list[str]):
    hr = "-" * 70
    print(hr)
    if tested == 0:
        assert not failed_files
        print("Nothing tested 😴")
        raise SystemExit(EXIT_NO_TESTS)
    print(f"{tested} {'test' if tested == 1 else 'tests'} run")
    if skipped:
        print(f"{skipped} {'test' if skipped == 1 else 'tests'} skipped")
    if failed == 0:
        assert not failed_files
        if skipped == 0:
            print("All tests passed 🎉")
        else:
            print("0 tests failed 🎉")
    else:
        assert failed_files
        print(
            f"{failed} {'test' if failed == 1 else 'tests'} failed "
            f"in {len(failed_files)} {'file' if len(failed_files) == 1 else 'files'} "
            "💥 (see above for details)"
        )
        for filename in failed_files:
            print(f" - {filename}")
        raise SystemExit(EXIT_FAILED)


def _print_version_and_exit():
    print(f"Groktest {__version__}")
    raise SystemExit(0)


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
        "--version",
        action="store_true",
        help="Show version and exit.",
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
    p.add_argument(
        "--last",
        action="store_true",
        help="Re-run last tests.",
    )
    p.add_argument(
        "-F",
        "--failfast",
        action="store_true",
        help="Stop on the first error for a file.",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Show debug info.",
    )
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


def _init_config(args: Any):
    config: ProjectConfig = {}
    _apply_args_config(args, config)
    if not args.paths:
        return config
    project_path = _project_candidate(args.paths[0])
    if not project_path:
        return config
    try:
        _apply_project_config(load_project_config(project_path), config)
    except ProjectDecodeError as e:
        log.debug("Error loading project config from %s: %s", project_path, e)
    else:
        if len(args.paths) > 1:
            raise SystemExit(
                f"extra arguments '{' '.join(args.paths[1:])}' to project "
                "path not currently supported"
            )
    return cast(ProjectConfig, config)


def _apply_args_config(args: Any, config: ProjectConfig):
    if args.failfast:
        config["failfast"] = True


def _apply_project_config(src: dict[str, Any], dest: dict[str, Any]):
    for key, src_val in src.items():
        try:
            dest_val = dest[key]
        except KeyError:
            dest[key] = src_val
        else:
            if isinstance(dest_val, dict) and isinstance(src_val, dict):
                _apply_project_config(src_val, dest_val)


def _project_candidate(path_arg: str):
    paths = [
        path_arg,
        os.path.join(path_arg, "pyproject.toml"),
        os.path.join(path_arg, "Cargo.toml"),
    ]
    for path in paths:
        if path[-5:].lower() == ".toml" and os.path.isfile(path):
            return path
    return None


def _test_filenames(config: Optional[ProjectConfig], args: Any):
    if not config:
        return args.paths
    include = _coerce_list(config.get("include"))
    if not include:
        raise SystemExit(
            f"Missing 'include' in 'tool.groktest' section in {config['__src__']}"
        )
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
