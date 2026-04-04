# sysaudit_menu.py
import os
import glob
import importlib.util
import inspect
import ast

PY_PATH = "./"
LARGE_FUNC_LINES = 30

exclude_files = {"syschkspxy.py", "exepxy.py", "sysexepxy.py"}

file_function_summary = {}
file_class_summary = {}
file_imports = {}
all_calls = set()
all_module_names = {}

# ------------------------------
# Utility Functions
# ------------------------------
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

def get_functions_classes(mod):
    funcs, classes = [], []
    for name, obj in inspect.getmembers(mod):
        if inspect.isfunction(obj):
            sig = str(inspect.signature(obj))
            doc = inspect.getdoc(obj)
            loc = len(inspect.getsourcelines(obj)[0])
            funcs.append({'name': name, 'sig': sig, 'doc': doc, 'lines': loc})
        elif inspect.isclass(obj):
            doc = inspect.getdoc(obj)
            methods = []
            for mname, mobj in inspect.getmembers(obj, inspect.isfunction):
                msig = str(inspect.signature(mobj))
                mdoc = inspect.getdoc(mobj)
                mloc = len(inspect.getsourcelines(mobj)[0])
                methods.append({'name': f"{name}.{mname}", 'sig': msig, 'doc': mdoc, 'lines': mloc})
            classes.append({'name': name, 'doc': doc, 'methods': methods})
    return funcs, classes

def analyze_ast(filepath):
    calls, imports, global_code = set(), set(), 0
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
        for stmt in tree.body:
            if not isinstance(stmt, (ast.FunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom, ast.If)):
                global_code += 1
    except Exception:
        pass
    return calls, imports, global_code

# ------------------------------
# Menu Options
# ------------------------------
def option_list_files():
    py_files = collect_py_files()
    print(f"\nFound {len(py_files)} files:\n")
    for f in py_files:
        print(f"  {os.path.relpath(f, PY_PATH)}")

def option_inspect_functions_classes():
    py_files = collect_py_files()
    for file in sorted(py_files):
        print("\n" + "="*50)
        print(f"File: {os.path.relpath(file, PY_PATH)}")
        mod = load_module(file)
        if not mod:
            print("  ERROR loading module.")
            continue
        funcs, classes = get_functions_classes(mod)
        file_function_summary[file] = funcs
        file_class_summary[file] = classes
        if funcs:
            print("  Functions:")
            for f in funcs:
                flags = []
                if not f['doc']:
                    flags.append("NO DOC")
                if f['lines'] > LARGE_FUNC_LINES:
                    flags.append(f"LARGE")
                print(f"    {f['name']}{f['sig']} {' '.join(flags)}")
        else:
            print("  No functions found.")
        if classes:
            print("  Classes:")
            for c in classes:
                flags = ["NO DOC"] if not c['doc'] else []
                print(f"    {c['name']} {' '.join(flags)}")
                for m in c['methods']:
                    mflags = []
                    if not m['doc']:
                        mflags.append("NO DOC")
                    if m['lines'] > LARGE_FUNC_LINES:
                        mflags.append("LARGE")
                    print(f"      {m['name']}{m['sig']} {' '.join(mflags)}")
        else:
            print("  No classes found.")

def option_analyze_calls_imports():
    py_files = collect_py_files()
    for file in sorted(py_files):
        calls, imports, global_code = analyze_ast(file)
        all_calls.update(calls)
        file_imports[file] = imports
        print("\n" + "="*50)
        print(f"File: {os.path.relpath(file, PY_PATH)}")
        print(f"  Calls: {', '.join(calls) if calls else 'None'}")
        print(f"  Imports: {', '.join(imports) if imports else 'None'}")
        print(f"  Global code lines: {global_code}")

def option_orphan_functions():
    orphan_functions = {}
    for file, funcs in file_function_summary.items():
        orphans = [f['name'] for f in funcs if f['name'].split('.')[-1] not in all_calls]
        if orphans:
            orphan_functions[file] = orphans
    for file, funcs in orphan_functions.items():
        print(f"\n{os.path.relpath(file, PY_PATH)}:")
        for f in funcs:
            print(f"  {f}")

def option_orphan_classes():
    orphan_classes = {}
    for file, classes in file_class_summary.items():
        orphans = []
        for c in classes:
            method_orphan = all(m['name'].split('.')[-1] not in all_calls for m in c['methods'])
            if method_orphan:
                orphans.append(c['name'])
        if orphans:
            orphan_classes[file] = orphans
    for file, classes in orphan_classes.items():
        print(f"\n{os.path.relpath(file, PY_PATH)}:")
        for c in classes:
            print(f"  {c}")

def option_orphan_files():
    imported_modules = set()
    for imps in file_imports.values():
        imported_modules.update(imps)
    py_files = collect_py_files()
    for f in py_files:
        mod_name = os.path.splitext(os.path.basename(f))[0]
        all_module_names[mod_name] = f
    orphan_files = []
    for mod_name, file in all_module_names.items():
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            has_main = '__name__' in content and '__main__' in content
        if mod_name not in imported_modules and not has_main:
            orphan_files.append(file)
    print(f"\nOrphan files ({len(orphan_files)}):")
    for f in orphan_files:
        print(f"  {os.path.relpath(f, PY_PATH)}")

# ------------------------------
# Menu Loop
# ------------------------------
def main():
    while True:
        print("\n" + "#"*40)
        print("PYX AUDIT MENU")
        print("#"*40)
        print("1. List all *pxy.py files")
        print("2. Inspect functions and classes")
        print("3. Analyze function calls and imports")
        print("4. Detect orphan functions")
        print("5. Detect orphan classes")
        print("6. Detect orphan files")
        print("7. Exit")
        choice = input("\nSelect option [1-7]: ").strip()
        if choice == "1":
            option_list_files()
        elif choice == "2":
            option_inspect_functions_classes()
        elif choice == "3":
            option_analyze_calls_imports()
        elif choice == "4":
            option_orphan_functions()
        elif choice == "5":
            option_orphan_classes()
        elif choice == "6":
            option_orphan_files()
        elif choice == "7":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()
