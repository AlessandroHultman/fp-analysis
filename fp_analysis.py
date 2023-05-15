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


ext_to_folder = {
    ".c": "c-results",
    ".cpp": "cpp-results",
    ".rs": "rust-results",
    ".hs": "haskell-results",
    ".rb": "ruby-results",
    ".java": "java-results",
    ".scala": "scala-results",
    ".m": "objective-c-results",
    ".swift": "swift-results",
}

lang_to_ext = {
    "c": ".c",
    "cpp": ".cpp",
    "rust": ".rs",
    "haskell": ".hs",
    "ruby": ".rb",
    "java": ".java",
    "scala": ".scala",
    "objective-c": ".m",
    "swift": ".swift",
}


# Run the compiler frontend corresponding to the language
def run_frontend(file_ext, file_path, file_name):
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


# Run the analysis pass with opt
def run_opt(file_name):
    subprocess.run(
        [
            "opt",
            "-disable-output",
            os.path.splitext(file_name)[0] + ".ll",
            "-passes=fp-module-analysis",
        ]
    )

def handle_io(base_name, csv_folder, file_ext):
    with open(base_name + ".csv", "r") as src, open(
        os.path.join(csv_folder, f"{ext_to_folder[file_ext]}" + ".csv"), "a"
    ) as dst:
        shutil.copyfileobj(src, dst)
        csv_folder = Path(csv_folder)
        shutil.move(base_name + ".csv", csv_folder)


def run_pass(dir, file_path):
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1]

    if file_ext in ext_to_folder.keys():
        run_frontend(file_ext, file_path, file_name)
    else:
        return

    run_opt(file_name)
    csv_folder = os.path.join(dir, ext_to_folder[file_ext])
    if not os.path.exists(csv_folder):
        os.mkdir(csv_folder)

    # Remove the generated .ll file
    file_name = file_name.strip()
    base_name = os.path.splitext(file_name)[0]
    print("remove")
    os.remove(base_name + ".ll")

    # If the pass is run on a Rust src file, .csv file gets created in current working directory
    if file_ext == ".rs":
        handle_io(base_name, csv_folder, file_ext)

    else:
        dir = os.path.expanduser(dir)
        file_name = os.path.join(dir, file_name)
        base_name = os.path.splitext(file_name)[0]
        handle_io(base_name, csv_folder, file_ext)


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

    langs = args.langs

    if not langs:
        pool = multiprocessing.Pool()
        # Run the analysis on all supported languages
        for root, dirs, files in os.walk(root_dir):
            for name in files:
                file_path = os.path.join(root, name)
                pool.apply(
                    run_pass,
                    (root_dir, file_path),
                )
        pool.close()
        pool.join()

    else:
        # Run the analysis only on the specified languages using multiprocessing
        pool = multiprocessing.Pool()
        for lang in langs:
            # Convert the language name to lower case and get the corresponding extension
            lang = lang.lower()
            if lang in lang_to_ext.keys():
                ext = lang_to_ext[lang]
                # Find all files with the matching extension and run the analysis on them using multiprocessing
                for root, dirs, files in os.walk(root_dir):
                    for name in files:
                        file_path = os.path.join(root, name)
                        if os.path.splitext(name)[1] == ext:
                            pool.apply(
                                run_pass,
                                (root_dir, file_path),
                            )
            else:
                print("Must enter supported language")

        pool.close()
        pool.join()

    print("Done.")
