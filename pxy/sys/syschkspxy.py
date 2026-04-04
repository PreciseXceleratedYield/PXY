# sysrun_inspect_pxy.py
import os
import glob
import subprocess
import importlib.util
import inspect

PY_PATH = "./"
exclude_files = {"syschkspxy.py", "exepxy.py", "sysexepxy.py"}

def collect_py_files():
    py_files = glob.glob(os.path.join(PY_PATH, "**", "*pxy.py"), recursive=True)
    return [f for f in py_files if os.path.basename(f) not in exclude_files]

def get_functions(filepath):
    """Load module and get top-level function names and signatures."""
    try:
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            return []
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        funcs = []
        for name, obj in inspect.getmembers(mod, inspect.isfunction):
            sig = str(inspect.signature(obj))
            funcs.append(f"{name}{sig}")
        return funcs
    except Exception as e:
        return [f"ERROR inspecting functions: {e}"]

def run_files():
    py_files = collect_py_files()
    if not py_files:
        print("No *pxy.py files found.")
        return

    success_count = 0
    fail_count = 0

    for file in sorted(py_files):
        print("\n" + "="*60)
        print(f"File: {os.path.relpath(file, PY_PATH)}")
        print("="*60)

        # 1️⃣ Show functions and signatures
        funcs = get_functions(file)
        if funcs:
            print("Functions & Signatures:")
            for f in funcs:
                print(f"  {f}")
        else:
            print("  No functions found.")

        # 2️⃣ Run the file
        try:
            subprocess.run(["python", file], check=True)
            print(f"✅ Execution successful: {os.path.basename(file)}")
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"❌ Execution failed: {os.path.basename(file)} - {e}")
            fail_count += 1

    # Final summary
    print("\n" + "#"*60)
    print("FINAL RUN SUMMARY")
    print(f"Total files: {len(py_files)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")
    print("#"*60)

if __name__ == "__main__":
    run_files()
