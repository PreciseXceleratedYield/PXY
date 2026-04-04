# syschecksigcpxy.py
import os
import glob
import importlib.util
import inspect

# Folder containing all *pxy.pyc files
PYC_PATH = "./"  # adjust if needed

def load_module_from_pyc(filepath):
    """Dynamically load a module from a .pyc file path"""
    module_name = os.path.splitext(os.path.basename(filepath))[0]
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def get_functions_from_module(mod):
    """Return list of (function_name, signature)"""
    functions = []
    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        sig = str(inspect.signature(obj))
        functions.append((name, sig))
    return functions

def main():
    # Recursively find all *pxy.pyc files
    pyc_files = glob.glob(os.path.join(PYC_PATH, "**", "*pxy.pyc"), recursive=True)
    print(f"Found {len(pyc_files)} *pxy.pyc files:\n")
    
    for file in sorted(pyc_files):
        print("="*60)
        print(f"File: {os.path.relpath(file, PYC_PATH)}")
        try:
            mod = load_module_from_pyc(file)
            funcs = get_functions_from_module(mod)
            if not funcs:
                print("  No functions found.")
            else:
                for name, sig in funcs:
                    print(f"  {name}{sig}")
        except Exception as e:
            print(f"  ERROR loading module: {e}")
        print("="*60 + "\n")

if __name__ == "__main__":
    main()
