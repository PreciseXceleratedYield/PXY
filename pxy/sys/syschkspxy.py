# sysaudit_full.py
import os
import glob
import importlib.util
import inspect
import ast

PY_PATH = "./"  # starting folder
LARGE_FUNC_LINES = 30  # threshold to flag large functions

file_function_summary = {}
file_class_summary = {}
file_imports = {}
all_calls = set()
all_module_names = {}

# -------------------------------
# Load module and inspect functions/classes
# -------------------------------
def load_module_from_py(filepath):
    module_name = os.path.splitext(os.path.basename(filepath))[0]
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def get_functions_and_classes(mod):
    funcs = []
    classes = []
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

# -------------------------------
# Parse AST for calls, imports, global code
# -------------------------------
def analyze_ast(filepath):
    calls = set()
    imports = set()
    global_code = 0
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=filepath)
        except SyntaxError:
            return calls, imports, global_code
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
    # Count top-level statements outside functions/classes
    for stmt in tree.body:
        if not isinstance(stmt, (ast.FunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom, ast.If)):
            global_code += 1
    return calls, imports, global_code

# -------------------------------
# Main processing
# -------------------------------
def main():
    global file_function_summary, file_class_summary, file_imports, all_calls, all_module_names

    py_files = glob.glob(os.path.join(PY_PATH, "**", "*pxy.py"), recursive=True)
    
    # Exclude the audit script itself to prevent self-loop
    py_files = [f for f in py_files if os.path.basename(f) != "syschkspxy.py"]

    print(f"Found {len(py_files)} *pxy.py files.\n")

    # Map module names to file paths
    for f in py_files:
        mod_name = os.path.splitext(os.path.basename(f))[0]
        all_module_names[mod_name] = f

    # Inspect each file
    for file in sorted(py_files):
        print("="*60)
        print(f"File: {os.path.relpath(file, PY_PATH)}")
        try:
            mod = load_module_from_py(file)
            funcs, classes = get_functions_and_classes(mod)
            file_function_summary[file] = funcs
            file_class_summary[file] = classes
            if funcs:
                print("  Functions:")
                for f in funcs:
                    flags = []
                    if not f['doc']:
                        flags.append("NO DOC")
                    if f['lines'] > LARGE_FUNC_LINES:
                        flags.append(f"LARGE({f['lines']} lines)")
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
                            mflags.append(f"LARGE({m['lines']} lines)")
                        print(f"      {m['name']}{m['sig']} {' '.join(mflags)}")
            else:
                print("  No classes found.")
        except Exception as e:
            print(f"  ERROR inspecting module: {e}")
            file_function_summary[file] = []
            file_class_summary[file] = []

        calls, imports, global_code = analyze_ast(file)
        all_calls.update(calls)
        file_imports[file] = imports
        print(f"  Function calls: {', '.join(calls) if calls else 'None'}")
        print(f"  Imports: {', '.join(imports) if imports else 'None'}")
        print(f"  Top-level global code lines: {global_code}")
        print("="*60 + "\n")

    # -------------------------------
    # Orphan functions
    # -------------------------------
    orphan_functions = {}
    for file, funcs in file_function_summary.items():
        orphans = []
        for f in funcs:
            simple_name = f['name'].split('.')[-1]
            if simple_name not in all_calls:
                orphans.append(f['name'])
        if orphans:
            orphan_functions[file] = orphans

    # -------------------------------
    # Orphan classes
    # -------------------------------
    orphan_classes = {}
    for file, classes in file_class_summary.items():
        orphans = []
        for c in classes:
            method_orphan = all(m['name'].split('.')[-1] not in all_calls for m in c['methods'])
            if method_orphan:
                orphans.append(c['name'])
        if orphans:
            orphan_classes[file] = orphans

    # -------------------------------
    # Orphan files (never imported & not main)
    # -------------------------------
    imported_modules = set()
    for imps in file_imports.values():
        imported_modules.update(imps)

    orphan_files = []
    for mod_name, file in all_module_names.items():
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            has_main = '__name__' in content and '__main__' in content
        if mod_name not in imported_modules and not has_main:
            orphan_files.append(file)

    # -------------------------------
    # Summary
    # -------------------------------
    print("\n" + "#"*80)
    print("FINAL AUDIT SUMMARY")
    print("#"*80)
    print(f"Total files found: {len(py_files)}")
    print(f"Orphan files: {len(orphan_files)}")
    for f in orphan_files:
        print(f"  {os.path.relpath(f, PY_PATH)}")

    print(f"\nOrphan functions (never called):")
    for file, funcs in orphan_functions.items():
        print(f"\n{os.path.relpath(file, PY_PATH)}:")
        for f in funcs:
            print(f"  {f}")

    print(f"\nOrphan classes (all methods never called):")
    for file, classes in orphan_classes.items():
        print(f"\n{os.path.relpath(file, PY_PATH)}:")
        for c in classes:
            print(f"  {c}")

if __name__ == "__main__":
    main()
