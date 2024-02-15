"""Test to confirm whether all of the OpenSBLI test cases are able to generate
code and compile without error.
"""

import os
import shutil
import subprocess
import multiprocessing


CHECK_DIFFERENCE = False

TEST_GENERATION = True
TEST_TRANSLATION = True
TEST_COMPILATION = True


def __run_process(commands: list, cwd: str) -> int:
    """_summary_

    Parameters
    ----------
    commands : list
        _description_
    cwd : str
        _description_

    Returns
    -------
    int
        _description_
    """
    try:
        rc = subprocess.run(
            commands,
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        if rc.returncode != 0:
            print(f"\033[91m{' '.join(commands)}\033[0m")
            print("\033[91m", rc.stderr.decode(), "\033[0m")
        return rc.returncode
    except Exception as e:
        print(f"An error occurred: {e}")
        return 1


def get_test_apps(root_dir: str) -> dict:
    """_summary_

    Parameters
    ----------
    root_dir : str
        _description_

    Returns
    -------
    dict
        _description_
    """
    return (
        f"{root_dir}/wave/wave.py",
        f"{root_dir}/euler_wave/euler_wave.py",
        f"{root_dir}/Sod_shock_tube/Sod_shock_tube.py",
        f"{root_dir}/taylor_green_vortex/TGsym/TGsym.py",
    )


def copy_app_to_test_dir(test_path: str, current_path: str, app_name: str) -> str:
    """_summary_

    Parameters
    ----------
    test_path : str
        _description_
    current_path : str
        _description_
    app_name : str
        _description_

    Returns
    -------
    str
        _description_
    """
    app_path = f"{test_path}/{app_name}/{app_name}.py"
    os.makedirs(os.path.dirname(app_path), exist_ok=True)
    shutil.copyfile(current_path, app_path)

    return app_path


def generate_app(app_file: str, app_dir: str) -> int:
    """_summary_

    Parameters
    ----------
    app_file : str
        _description_
    app_dir : str
        _description_

    Returns
    -------
    int
        _description_

    Raises
    ------
    ValueError
        _description_
    """
    if not app_file or not app_dir:
        raise ValueError("Both `app_file` and `app_dir` must be provided")

    return __run_process(["python", app_file], app_dir)


def translate_app(app_dir: str) -> int:
    """Compile the OpenSBLI app using OPS.

    Parameters
    ----------
    app_dir : str
        Directory where the compilation should occur.

    Returns
    -------
    int
        A status code indicating success (0) or failure.
    """
    if not app_dir:
        raise ValueError("app_dir must be provided.")

    translator = os.getenv("OPS_TRANSLATOR")
    if not translator:
        raise EnvironmentError("OPS_TRANSLATOR environment variable is not set.")

    return __run_process(["python", f"{translator}/ops.py", "opensbli.cpp"], app_dir)


def compile_app(app_dir: str) -> int:
    """_summary_

    Parameters
    ----------
    app_dir : str
        _description_

    Returns
    -------
    int
        _description_

    Raises
    ------
    ValueError
        _description_
    """
    if not app_dir:
        raise ValueError("app_dir must be provided.")

    # we need a Makefile to compile an OpenSBLI app
    shutil.copyfile(
        f"{os.getenv('OPENSBLI_INSTALL')}/apps/Makefile", f"{app_dir}/Makefile"
    )

    # compile for each use case
    for mode in ["seq", "mpi"]:
        rc = __run_process(
            ["make", "-j", str(multiprocessing.cpu_count()), "-B", f"opensbli_{mode}"],
            cwd=app_dir,
        )
        if rc:
            return rc

    return 0


def test():
    """Run the testing framework.

    Raises
    ------
    EnvironmentError
        _description_
    EnvironmentError
        _description_
    """
    if not os.getenv("OPENSBLI_INSTALL"):
        raise EnvironmentError("$OPENSBLI_INSTALL has not been set")
    if not os.getenv("OPS_TRANSLATOR"):
        raise EnvironmentError("$OPS_TRANSLATOR has not been set")

    test_dir = f"{os.getenv('OPENSBLI_INSTALL')}/tests"
    test_app_paths = get_test_apps(f"{os.getenv('OPENSBLI_INSTALL')}/apps")

    num_failed = 0
    num_passed = 0

    for app_path in test_app_paths:
        app_name = os.path.splitext(os.path.basename(app_path))[0]
        app_path = copy_app_to_test_dir(test_dir, app_path, app_name)
        app_file = os.path.basename(app_path)
        app_dir = os.path.dirname(app_path)
        print(f"Testing: {app_name}")

        # Test that OpenSBLI can generate the test case
        rc = generate_app(app_file, app_dir)
        if rc:
            print("Failed to generate")
            num_failed += 1
            continue

        # Test that OPS can translate the OpenSBLI code
        rc = translate_app(app_dir)
        if rc:
            print("Failed to translate")
            num_failed += 1
            continue

        # Test that the OPS translated code can compile
        rc = compile_app(app_dir)
        if rc:
            print("Failed to compile")
            num_failed += 1
            continue

        num_passed += 1
        print("\033[92mTest passed\033[0m")

    # shutil.rmtree(test_dir)


if __name__ == "__main__":
    test()
