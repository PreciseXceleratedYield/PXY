# sysrun_showcall.py
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
    """Return top-level function names and signatures."""
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
            funcs.append((name, sig))
        return funcs
    except Exception as e:
        return [("ERROR inspecting functions", str(e))]

def run_files():
    py_files = collect_py_files()
    if not py_files:
        print("No *pxy.py files found.")
        return

    for file in sorted(py_files):
        print("\n" + "="*60)
        print(f"File: {os.path.relpath(file, PY_PATH)}")
        print("="*60)

        # 1️⃣ Show functions and “how to call them”
        funcs = get_functions(file)
        if funcs:
            print("Functions & How to Call:")
            for name, sig in funcs:
                print(f"  {name}{sig}  --> Call: {name}{sig}")
        else:
            print("  No functions found.")

        # 2️⃣ Run the file
        try:
            subprocess.run(["python", file], check=True)
            print(f"✅ Execution successful")
        except subprocess.CalledProcessError as e:
            print(f"❌ Execution failed: {e}")

if __name__ == "__main__":
    run_files()
