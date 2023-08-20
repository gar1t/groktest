# SPDX-License-Identifier: Apache-2.0

from typing import *

import argparse
import json
import logging
import os
import tempfile

from .__init__ import test_file


def _init_logging(args: Any):
    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(levelname)s: [%(name)s] %(message)s",
        )


def _test_filenames(args: Any):
    if args.last:
        last = _last_run()
        if not last:
            raise SystemExit(
                "last not found - run at least one test before using '--last'"
            )
        return last
    return args.paths


def _last_run():
    try:
        f = open(_last_run_savefile())
    except FileNotFoundError:
        return None
    else:
        with f:
            return json.load(f)


def _save_last_run(filenames: List[str]):
    filenames = [os.path.abspath(path) for path in filenames]
    with open(_last_run_savefile(), "w") as f:
        json.dump(filenames, f)


def _last_run_savefile():
    return os.path.join(tempfile.gettempdir(), "groktest.last")


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "paths",
        metavar="PATH",
        type=str,
        help="file to test",
        nargs="*",
    )
    p.add_argument("--last", action="store_true", help="re-run last tests")
    p.add_argument("--debug", action="store_true", help="show debug info")
    args = p.parse_args()
    _init_logging(args)

    failed = tested = 0

    to_run = _test_filenames(args)
    _save_last_run(to_run)

    for filename in to_run:
        print(f"Testing {filename}")
        result = test_file(filename)
        failed += result["failed"]
        tested += result["tested"]

    assert failed <= tested, (failed, tested)
    if tested == 0:
        print("Nothing tested")
    elif failed == 0:
        print("All tests passed 🔥")
    else:
        print("Tests failed - see above for details")


if __name__ == "__main__":
    main()
