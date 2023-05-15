#!/usr/bin/env python3

# A script to run the floating-point analysis pass on all source code files
# that can be generated as LLVM IR
# Assuming the script is run from any directory and takes the root directory as an argument

import os
import shutil
import subprocess
import argparse
import multiprocessing
from pathlib import Path


def run_pass(dir, output_file, file_path, csv_folder):
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1]

    if file_ext == ".c":
        # Generate the LLVM IR file with clang
        subprocess.run(["clang", "-emit-llvm", "-S", file_path])
    elif file_ext == ".cpp":
        # Generate the LLVM IR file with clang++
        subprocess.run(["clang++", "-emit-llvm", "-S", file_path])
    elif file_ext == ".hs":
        # Generate the LLVM IR file with ghc
        subprocess.run(["ghc", "-fllvm", "-keep-llvm-files", "-O2", file_path])
    elif file_ext == ".rs":
        # Generate the LLVM IR file with rustc
        subprocess.run(["rustc", "--emit=llvm-ir", file_path])
    elif file_ext == ".java":
        # Generate the LLVM IR file with llvmc
        subprocess.run(["llvmc", "-emit-llvm", file_path])
    elif file_ext == ".swift":
        # Generate the LLVM IR file with swiftc
        subprocess.run(["swiftc", "-emit-ir", file_path])
    elif file_ext == ".scala":
        # Generate the LLVM IR file with scalac and llvm-dis
        subprocess.run(["scalac", "-Xassem-extdirs", ".", file_path])
        subprocess.run(["llvm-dis", os.path.splitext(file_name)[0] + ".s"])
        os.remove(os.path.splitext(file_name)[0] + ".s")
    elif file_ext == ".m":
        # Generate the LLVM IR file with clang
        subprocess.run(["clang", "-emit-llvm", "-S", file_path, "-fobjc-arc"])
    elif file_ext == ".rb":
        # Generate the LLVM IR file with ruby-llvm
        subprocess.run(["ruby-llvm", "--emit-llvm", file_path])
    else:
        return

    # Run the analysis pass with opt and append the output to the output file
    subprocess.run(
        [
            "opt",
            "-disable-output",
            os.path.splitext(file_name)[0] + ".ll",
            "-passes=fp-module-analysis",
        ]
    )

    file_name = file_name.strip()
    base_name = os.path.splitext(file_name)[0]

    os.remove(base_name + ".ll")

    # If the pass is run on a Rust src file, .csv file gets created in current working directory
    if file_ext == ".rs":
        with open(base_name + ".csv", "r") as src, open(output_file, "a") as dst:
            shutil.copyfileobj(src, dst)

        csv_folder = os.path.join(dir, "file-results")
        csv_folder = Path(csv_folder)

        shutil.move(base_name + ".csv", csv_folder)
    else:
        dir = os.path.expanduser(dir)
        file_name = os.path.join(dir, file_name)
        base_name = os.path.splitext(file_name)[0]

        with open(base_name + ".csv", "r") as src, open(output_file, "a") as dst:
            shutil.copyfileobj(src, dst)

        csv_folder = os.path.join(dir, "file-results")
        csv_folder = Path(csv_folder)

        shutil.move(base_name + ".csv", csv_folder)


# Check if the module is being run as the main program or not
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the floating-point analysis pass on source code files"
    )
    parser.add_argument("--dir", help="the root directory for the analysis")
    parser.add_argument(
        "--langs", nargs="*", help="the programming languages to analyze"
    )
    args = parser.parse_args()

    root_dir = args.dir
    root_dir = os.path.expanduser(root_dir)
    if not os.path.isdir(root_dir):
        print(f"{root_dir} is not a valid directory.")
        exit(1)

    # Create an empty output file in the root directory
    output_file = os.path.join(root_dir, "results.csv")

    # Create a folder for the csv files in the root directory
    csv_folder = os.path.join(root_dir, "file-results")
    os.makedirs(csv_folder, exist_ok=True)

    langs = args.langs

    if not langs:
        pool = multiprocessing.Pool()
        # Run the analysis on all supported languages
        for root, dirs, files in os.walk(root_dir):
            for name in files:
                pool.apply_async(
                    run_pass,
                    (
                        root_dir,
                        output_file,
                        os.path.join(root, name),
                        csv_folder,
                    ),
                )
        pool.close()
        pool.join()

    else:
        # Run the analysis only on the specified languages using multiprocessing
        pool = multiprocessing.Pool()
        for lang in langs:
            # Convert the language name to lower case and get the corresponding extension
            lang = lang.lower()
            if lang == "c":
                ext = "c"
            elif lang == "c++":
                ext = "cpp"
            elif lang == "haskell":
                ext = "hs"
            elif lang == "rust":
                ext = "rs"
            elif lang == "java":
                ext = "java"
            elif lang == "swift":
                ext = "swift"
            elif lang == "scala":
                ext = "scala"
            elif lang == "objective-c":
                ext = "m"
            elif lang == "ruby":
                ext = "rb"
            else:
                continue

            # Find all files with the matching extension and run the analysis on them using multiprocessing
            for root, dirs, files in os.walk(root_dir):
                for name in files:
                    if os.path.splitext(name)[1] == "." + ext:
                        pool.apply_async(
                            run_pass,
                            (
                                root_dir,
                                output_file,
                                os.path.join(root, name),
                                csv_folder,
                            ),
                        )

        pool.close()
        pool.join()

    print(f"Done. Check {output_file} and {csv_folder}.")
