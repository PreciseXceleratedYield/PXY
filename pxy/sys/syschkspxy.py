# sysaudit_simple.py
import os
import glob
import importlib.util
import inspect
import py_compile

PY_PATH = "./"
exclude_files = {"syschkspxy.py", "exepxy.py", "sysexepxy.py"}

file_function_summary = {}
file_syntax_summary = {}

# -----------------------------
# Utility Functions
# -----------------------------
def collect_py_files():
    py_files = glob.glob(os.path.join(PY_PATH, "**", "*pxy.py"), recursive=True)
    return [f for f in py_files if os.path.basename(f) not in exclude_files]

def load_module(filepath):
    try:
        module_name = os.path.splitext(os.path.basename(filepath))[0]
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None

def get_functions(mod):
    funcs = []
    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        sig = str(inspect.signature(obj))
        funcs.append({'name': name, 'sig': sig})
    return funcs

def check_syntax(filepath):
    try:
        py_compile.compile(filepath, doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e)

# -----------------------------
# Menu Options
# -----------------------------
def option_list_files():
    py_files = collect_py_files()
    print(f"\nFound {len(py_files)} files:\n")
    for f in py_files:
        print(f"  {os.path.relpath(f, PY_PATH)}")

def option_inspect_functions():
    py_files = collect_py_files()
    for file in sorted(py_files):
        print("\n" + "="*50)
        print(f"File: {os.path.relpath(file, PY_PATH)}")
        mod = load_module(file)
        if not mod:
            print("  ERROR loading module")
            continue
        funcs = get_functions(mod)
        file_function_summary[file] = funcs
        if funcs:
            for f in funcs:
                print(f"  {f['name']}{f['sig']}")
        else:
            print("  No functions found.")

def option_syntax_check():
    py_files = collect_py_files()
    for file in sorted(py_files):
        ok, msg = check_syntax(file)
        file_syntax_summary[file] = ok
        status = "OK" if ok else "ERROR"
        print(f"{os.path.relpath(file, PY_PATH)} : {status}")
        if msg:
            print(f"  {msg}")

def option_summary():
    print("\n" + "#"*50)
    print("SUMMARY PER FILE")
    print("#"*50)
    py_files = collect_py_files()
    for file in sorted(py_files):
        funcs = file_function_summary.get(file, [])
        syntax_ok = file_syntax_summary.get(file, None)
        syntax_status = "OK" if syntax_ok else ("Not Checked" if syntax_ok is None else "ERROR")
        print(f"\nFile: {os.path.relpath(file, PY_PATH)}")
        print(f"  Functions found: {len(funcs)}")
        print(f"  Syntax check: {syntax_status}")

# -----------------------------
# Menu Loop
# -----------------------------
def main():
    while True:
        print("\n" + "#"*40)
        print("PYX SIMPLE AUDIT MENU")
        print("#"*40)
        print("1. List all *pxy.py files")
        print("2. Inspect functions (signatures only)")
        print("3. Syntax check each file")
        print("4. Summary per file")
        print("5. Exit")
        choice = input("\nSelect option [1-5]: ").strip()
        if choice == "1":
            option_list_files()
        elif choice == "2":
            option_inspect_functions()
        elif choice == "3":
            option_syntax_check()
        elif choice == "4":
            option_summary()
        elif choice == "5":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()
