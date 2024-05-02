# SPDX-License-Identifier: Apache-2.0

from typing import *

from .__init__ import ProjectConfig

import argparse
import glob
import io
import json
import logging
import os
import queue
import sys
import tempfile
import threading

from .__init__ import __version__
from .__init__ import test_file
from .__init__ import load_project_config
from .__init__ import ProjectDecodeError
from .__init__ import TestSummary
from .__init__ import TestTypeNotSupported

# Defer init to `_init_logging()`
log: logging.Logger = cast(logging.Logger, None)

EXIT_FAILED = 1
EXIT_NO_TESTS = 2


class TestQueue(queue.Queue):
    def __init__(self, filenames: list[str]):
        super().__init__()
        self.tests = [ConcurrentTest(filename) for filename in filenames]
        for test in self.tests:
            self.put(test)

    def __iter__(self):
        return iter(self.tests)


class TestRunner(threading.Thread):
    def __init__(self, queue: TestQueue, config: ProjectConfig):
        super().__init__()
        self.queue = queue
        self.config = config
        self.start()

    def run(self):
        while True:
            try:
                test = self.queue.get(block=False)
            except queue.Empty:
                break
            else:
                try:
                    result = test_file(test.filename, self.config, test.print_result)
                except Exception as e:
                    test.set_result(e)
                else:
                    test.set_result(result)


class ConcurrentTest:
    def __init__(self, filename: str):
        self.filename = filename
        self._result: Optional[Union[TestSummary, Exception]] = None
        self._has_result = threading.Event()
        self._output = io.StringIO()

    def __str__(self):
        return os.path.relpath(self.filename)

    def print_result(self, s: str):
        self._output.write(s)
        self._output.write("\n")

    def set_result(self, result: TestSummary | Exception):
        self._result = result
        self._has_result.set()

    def wait_for_result(self):
        self._has_result.wait()
        assert self._result
        return self._result

    def get_output(self):
        out = self._output.getvalue()
        return out[:-1] if out else out


class ResultSummary:
    failed: int = 0
    tested: int = 0
    skipped: int = 0
    failed_files: list[str] = []


def main(args: Any = None):
    args = args or sys.argv[1:]
    p = _init_parser()
    args = p.parse_args(args)
    if args.version:
        _print_version_and_exit()

    _init_logging(args)
    _apply_last(args)
    config = _init_config(args)

    queue = TestQueue(sorted(_test_filenames(config, args)))
    if args.preview:
        _preview_and_exit(queue)

    runners = _init_runners(queue, config, args)
    summary = ResultSummary()
    for test in queue:
        print(f"Testing {test}")
        result = test.wait_for_result()
        output = test.get_output()
        if output:
            print(output)
        _handle_test_result(test.filename, result, summary)
    _join_runners(runners)
    _print_result_summary(summary)


def _preview_and_exit(queue: TestQueue):
    for test in queue:
        print(f"Testing {test} (preview)")
    raise SystemExit(0)


def _init_runners(queue: TestQueue, config: ProjectConfig, args: Any):
    return [
        TestRunner(queue, config)
        for _ in range(args.concurrency or _default_concurrency())
    ]


def _default_concurrency():
    return 8


def _join_runners(runners: list[TestRunner]):
    for runner in runners:
        runner.join()


def _handle_test_result(
    filename: str,
    result: TestSummary | Exception,
    summary: ResultSummary,
):
    if isinstance(result, Exception):
        _handle_test_error(filename, result)
    else:
        assert isinstance(result, TestSummary)
        if result.failed:
            summary.failed_files.append(filename)
        summary.failed += result.failed
        summary.tested += result.tested
        summary.skipped += result.skipped


def _handle_test_error(filename: str, e: Exception):
    if isinstance(e, FileNotFoundError):
        log.warning("%s does not exist, skipping", filename)
    elif isinstance(e, IsADirectoryError):
        log.warning("%s is a directory, skipping", filename)
    elif isinstance(e, TestTypeNotSupported):
        log.warning("Test type '%s' for %s is not supported, skipping", e, filename)
    else:
        log.error("Unhandled error for %s: %r", filename, e)


def _print_result_summary(summary: ResultSummary):
    tested = summary.tested
    skipped = summary.skipped
    failed = summary.failed
    failed_files = summary.failed_files

    print("-" * 70)
    if tested == 0:
        assert not failed_files
        print("Nothing tested 😴")
        raise SystemExit(EXIT_NO_TESTS)

    print(f"{tested} {'test' if tested == 1 else 'tests'} run")
    if skipped:
        print(f"{skipped} {'test' if skipped == 1 else 'tests'} skipped")
    if failed == 0:
        assert not failed_files
        print("All tests passed 🎉")
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
        "-C",
        "--concurrency",
        metavar="N",
        type=int,
        help="Max number of concurrent tests.",
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
        config.setdefault("options", []).append("+failfast")


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


def _test_filenames(config: ProjectConfig, args: Any):
    if "__src__" not in config:
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
