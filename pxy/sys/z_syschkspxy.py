# sysrun_select.py
import os
import glob
import importlib.util
import inspect
import subprocess

BASE_PATH = "./"
exclude_files = {"syschkspxy.py", "exepxy.py", "sysexepxy.py"}

# -------------------------
# Get folders
# -------------------------
def get_folders():
    folders = set()
    for root, dirs, files in os.walk(BASE_PATH):
        for file in files:
            if file.endswith("pxy.py") and file not in exclude_files:
                folders.add(root)
    return sorted(list(folders))

# -------------------------
# Get files in folder
# -------------------------
def get_files(folder):
    files = glob.glob(os.path.join(folder, "*pxy.py"))
    return [f for f in files if os.path.basename(f) not in exclude_files]

# -------------------------
# Show functions
# -------------------------
def show_functions(file):
    try:
        module_name = os.path.splitext(os.path.basename(file))[0]
        spec = importlib.util.spec_from_file_location(module_name, file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        print("\nFunctions & How to Call:\n")
        for name, obj in inspect.getmembers(mod, inspect.isfunction):
            sig = str(inspect.signature(obj))
            print(f"  {name}{sig}  --> {name}{sig}")
    except Exception as e:
        print(f"Error loading module: {e}")

# -------------------------
# Run file
# -------------------------
def run_file(file):
    print("\nRunning file...\n")
    try:
        subprocess.run(["python", file])
        print("\n✅ Done")
    except Exception as e:
        print(f"\n❌ Error: {e}")

# -------------------------
# Main flow
# -------------------------
def main():
    # Step 1: Folder menu
    folders = get_folders()
    if not folders:
        print("No folders with *pxy.py files found.")
        return

    print("\nFOLDERS:\n")
    for i, f in enumerate(folders, 1):
        print(f"{i}. {f}")

    choice = input("\nSelect folder number: ").strip()
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(folders):
        print("Invalid choice")
        return

    selected_folder = folders[int(choice) - 1]

    # Step 2: File menu
    files = get_files(selected_folder)
    if not files:
        print("No *pxy.py files in this folder.")
        return

    print("\nFILES:\n")
    for i, f in enumerate(files, 1):
        print(f"{i}. {os.path.basename(f)}")

    choice = input("\nSelect file number: ").strip()
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(files):
        print("Invalid choice")
        return

    selected_file = files[int(choice) - 1]

    print("\n" + "="*60)
    print(f"Selected: {selected_file}")
    print("="*60)

    # Step 3: Show functions
    show_functions(selected_file)

    # Step 4: Run file
    run_file(selected_file)

# -------------------------
if __name__ == "__main__":
    main()
