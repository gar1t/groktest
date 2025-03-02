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
from .__init__ import Panic
from .__init__ import ProjectDecodeError
from .__init__ import Test
from .__init__ import TestSummary
from .__init__ import TestTypeNotSupported
from .__init__ import decode_options
from .__init__ import load_project_config
from .__init__ import parse_front_matter
from .__init__ import test_file

# Defer init to `_init_logging()`
log: logging.Logger = cast(logging.Logger, None)

EXIT_FAILED = 1
EXIT_NO_TESTS = 2


stdout_lock = threading.Lock()


def _safe_print(s: str):
    assert stdout_lock.locked()
    sys.stdout.write(s)
    sys.stdout.write("\n")


print = _safe_print


class ConcurrentTest:
    def __init__(self, filename: str):
        self.filename = filename
        self._result: Optional[Union[TestSummary, Exception]] = None
        self._has_result = threading.Event()
        self._output = io.StringIO()

    def __str__(self):
        return os.path.relpath(self.filename)

    def print_output(self, s: str):
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

    def reset_output(self):
        self._output = io.StringIO()


class TestQueue(queue.Queue[ConcurrentTest]):
    def __init__(self, filenames: list[str]):
        super().__init__()
        self.tests = [ConcurrentTest(filename) for filename in filenames]
        for test in self.tests:
            self.put(test)

    def __iter__(self):
        return iter(self.tests)


class TestFileRunner(threading.Thread):
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
                    _run_test(test, self.config)
                except Exception as e:
                    if log.getEffectiveLevel() <= logging.DEBUG:
                        log.exception(test.filename)
                    test.set_result(e)


def _run_test(test: ConcurrentTest, config: ProjectConfig):
    trial = Trial(test)
    while trial.run_or_retry():
        result = test_file(test.filename, config, test.print_output)
        trial.handle_result(result)


class Trial:

    def __init__(self, test: ConcurrentTest):
        self._test = test
        self._retry_on_fail_max = _retry_on_fail_test_option(test.filename)
        self._run_count = 0
        self._result: TestSummary | None = None

    def handle_result(self, result: TestSummary):
        self._run_count += 1
        self._result = result
        if self._retry_pending():
            _handle_test_retry(self._test, self._run_count, self._retry_on_fail_max)
        else:
            self._test.set_result(result)

    def run_or_retry(self):
        return self._run_count == 0 or self._retry_pending()

    def _retry_pending(self):
        return self._failed() and self._run_count <= self._retry_on_fail_max

    def _failed(self):
        return self._result is not None and len(self._result.failed) > 0


def _handle_test_retry(test: ConcurrentTest, cur_retry: int, max_retries: int):
    output = test.get_output()
    if output:
        print(output)
        test.reset_output()
    print(f"Retrying {test} ({cur_retry} of {max_retries})")


def _retry_on_fail_test_option(test_filename: str):
    fm = _parse_front_matter(test_filename)
    encoded_options = fm.get("test-options")
    if not encoded_options:
        return 0
    options = decode_options(encoded_options)
    val = options.get("retry-on-fail")
    if val is None:
        return 0
    elif not isinstance(val, int):
        log.warning(
            "Invalid value for retry-on-fail in \"%s\": expect int", test_filename
        )
        return 0
    return val


def _parse_front_matter(filename: str):
    # This is intentionally different from the front matter parse in
    # __init__ as we're only interested in test config here. We read
    # only a much of the file as needed to parse front matter.
    fm_lines: list[str] = []
    in_fm = False
    with open(filename) as f:
        while True:
            line = f.readline()
            if not line:
                break
            line = line.rstrip()
            if not line and not in_fm:
                continue
            elif line == "---":
                fm_lines.append(line)
                if in_fm:
                    break
                in_fm = True
            elif not in_fm:
                break
            else:
                fm_lines.append(line)

    return parse_front_matter("\n".join(fm_lines), filename)


class TestLocation:
    def __init__(self, filename: str, line: int):
        self.filename = filename
        self.line = line


class ResultSummary:
    def __init__(self):
        self.failed: list[TestLocation] = []
        self.tested: list[TestLocation] = []
        self.skipped: list[TestLocation] = []


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
        with stdout_lock:
            print(f"Testing {test}")
        with stdout_lock:
            result = test.wait_for_result()
        output = test.get_output()
        if output:
            with stdout_lock:
                print(output)
        _handle_test_result(test.filename, result, summary)
    _join_runners(runners)
    with stdout_lock:
        _print_summary_and_exit(summary, config)


def _preview_and_exit(queue: TestQueue):
    for test in queue:
        print(f"Testing {test} (preview)")
    raise SystemExit(0)


def _init_runners(queue: TestQueue, config: ProjectConfig, args: Any):
    return [
        TestFileRunner(queue, config)
        for _ in range(args.concurrency or _default_concurrency())
    ]


def _default_concurrency():
    return 8


def _join_runners(runners: list[TestFileRunner]):
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
        summary.failed.extend(_to_summary_tests(result.failed))
        summary.tested.extend(_to_summary_tests(result.tested))
        summary.skipped.extend(_to_summary_tests(result.skipped))


def _to_summary_tests(tests: list[Test]):
    return [TestLocation(t.filename, t.line) for t in tests]


def _handle_test_error(filename: str, e: Exception):
    if isinstance(e, FileNotFoundError):
        log.warning("%s does not exist, skipping", filename)
    elif isinstance(e, IsADirectoryError):
        log.warning("%s is a directory, skipping", filename)
    elif isinstance(e, TestTypeNotSupported):
        log.warning("Test type '%s' for %s is not supported, skipping", e, filename)
    elif isinstance(e, Panic):
        log.error(
            "Stopped testing %s because of an unhandled error - "
            "refer to the log above for the source test",
            filename,
        )
    else:
        raise AssertionError((filename, e))


def _print_summary_and_exit(summary: ResultSummary, config: ProjectConfig):
    print("-" * 70)
    if not summary.tested:
        print("Nothing tested 😴")
        raise SystemExit(EXIT_NO_TESTS)

    _print_tested_count(summary.tested)
    if summary.skipped:
        _print_skipped(summary.skipped, config)
    if summary.failed:
        _print_failed(summary.failed, config)
        raise SystemExit(EXIT_FAILED)
    print("All tests passed 🎉")
    raise SystemExit(0)


def _print_tested_count(tested: list[TestLocation]):
    print(f"{len(tested)} {'test' if len(tested) == 1 else 'tests'} run")


def _print_skipped(skipped: list[TestLocation], config: ProjectConfig):
    show_skipped = config.get("show-skipped")
    print(
        f"{len(skipped)} {'test' if len(skipped) == 1 else 'tests'} skipped"
        f"{'' if show_skipped else ' (use --show-skipped to view)'}"
    )
    if config.get("show-skipped"):
        for test in skipped:
            print(f" - {os.path.relpath(test.filename)}:{test.line}")


def _print_failed(failed: list[TestLocation], config: ProjectConfig):
    print(
        f"{len(failed)} {'test' if len(failed) == 1 else 'tests'} failed "
        "💥 (see above for details)"
    )
    for test in failed:
        print(f" - {os.path.relpath(test.filename)}:{test.line}")


def _print_version_and_exit():
    with stdout_lock:
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
        "-f",
        "--fail-fast",
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
        "--show-skipped",
        action="store_true",
        help="Show skipped tests in output.",
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
        if os.getenv("NO_SAVE_LAST") != "1":
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
    if args.fail_fast:
        config["fail-fast"] = True
    if args.show_skipped:
        config["show-skipped"] = True


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
