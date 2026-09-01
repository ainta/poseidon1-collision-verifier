#!/usr/bin/env python3
"""Run the collision witness through the pinned official verifier."""

import importlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


OFFICIAL_REPOSITORY = "https://github.com/khovratovich/poseidon-tools.git"
OFFICIAL_COMMIT = "60075da7c0521d9493749a035b1f30d4eda37138"
HERE = Path(__file__).resolve().parent


def run(command, cwd, input_text=None):
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True,
            input=input_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.strip()
    except FileNotFoundError as error:
        raise SystemExit(f"Required program not found: {command[0]}") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip()
        raise SystemExit(f"Command failed: {' '.join(command)}\n{detail}") from error


def fetch_official_verifier(destination):
    destination.mkdir()
    run(["git", "init", "--quiet"], destination)
    run(["git", "remote", "add", "origin", OFFICIAL_REPOSITORY], destination)
    run(
        ["git", "fetch", "--quiet", "--depth", "1", "origin", OFFICIAL_COMMIT],
        destination,
    )
    run(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], destination)

    actual_commit = run(["git", "rev-parse", "HEAD"], destination)
    if actual_commit != OFFICIAL_COMMIT:
        raise SystemExit(
            f"Wrong official commit: expected {OFFICIAL_COMMIT}, got {actual_commit}"
        )
    return actual_commit


def load_official_verifier(repository):
    sys.path.insert(0, str(repository))
    return importlib.import_module("bounties.partial_collision_verifier")


def verify_mds_independently(matrix, prime, build_directory):
    size = len(matrix)
    if size == 0 or any(len(row) != size for row in matrix):
        raise SystemExit("M must be a non-empty square matrix.")

    compiler = next(
        (path for name in ("c++", "clang++", "g++") if (path := shutil.which(name))),
        None,
    )
    if compiler is None:
        raise SystemExit("A C++17 compiler is required for the independent MDS check.")

    binary = build_directory / "verify_mds"
    run(
        [
            compiler,
            "-std=c++17",
            "-O3",
            "-pthread",
            str(HERE / "verify_mds.cpp"),
            "-o",
            str(binary),
        ],
        HERE,
    )
    matrix_input = "\n".join(
        [f"{size} {prime}", *(" ".join(map(str, row)) for row in matrix)]
    )
    output = run([str(binary)], HERE, input_text=matrix_input)
    result = output.splitlines()[-1] if output else ""
    if result != "ALL_NONEMPTY_SQUARE_MINORS_NONZERO":
        raise SystemExit(f"Independent MDS verification failed:\n{output}")
    return result


def main():
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 or later is required.")

    solution = json.loads((HERE / "solution.json").read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="poseidon-official-") as temporary:
        official_repository = Path(temporary) / "poseidon-tools"
        actual_commit = fetch_official_verifier(official_repository)
        official = load_official_verifier(official_repository)

        expected_parameters = {
            "official_commit": OFFICIAL_COMMIT,
            "p": official.COLLISION_P,
            "alpha": official.COLLISION_ALPHA,
            "width": official.COLLISION_TPERM,
            "RF": official.COLLISION_RF,
            "RP": official.COLLISION_RP,
            "prefix": official.SEED,
        }
        for name, expected in expected_parameters.items():
            if solution.get(name) != expected:
                raise SystemExit(
                    f"solution.json has {name}={solution.get(name)!r}; expected {expected!r}"
                )

        matrix = solution["M"]
        x = solution["X"]
        y = solution["Y"]

        poseidon = official.Poseidon(
            prime=official.COLLISION_P,
            alpha=official.COLLISION_ALPHA,
            t=official.COLLISION_TPERM,
            r_f=official.COLLISION_RF,
            r_p=official.COLLISION_RP,
            mds=matrix,
            round_constants=None,
        )
        hash_x = official._hash(
            x,
            poseidon,
            official.COLLISION_P,
            official.COLLISION_ELL,
            official.COLLISION_TPERM,
        )
        hash_y = official._hash(
            y,
            poseidon,
            official.COLLISION_P,
            official.COLLISION_ELL,
            official.COLLISION_TPERM,
        )

        verified = official.verify_collision_solution(x, y, t=16, mds=matrix)
        independent_mds = verify_mds_independently(
            matrix,
            official.COLLISION_P,
            Path(temporary),
        )

    print("official_commit", actual_commit)
    print("X_distinct_Y", x != y)
    print("H(X)", hash_x)
    print("H(Y)", hash_y)
    print("official_t16", verified)
    print("independent_mds", independent_mds)

    if x == y or hash_x != hash_y or not verified:
        raise SystemExit("Verification failed.")


if __name__ == "__main__":
    main()
