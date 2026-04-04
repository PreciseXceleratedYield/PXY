# syschkspxy.py

import subprocess
import glob
import os

def run_pxy_files_one_by_one(folder="."):
    """
    Run all *.pyc files in the folder one by one.
    After each run, wait for user input to continue.
    """
    pyc_files = glob.glob(os.path.join(folder, "*.pyc"))
    if not pyc_files:
        print("No .pyc files found in folder:", folder)
        return

    for file in pyc_files:
        print("\n" + "="*50)
        print(f"Running: {os.path.basename(file)}")
        print("="*50)
        try:
            subprocess.run(["python", file], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running {file}: {e}")

        # Prompt to continue
        proceed = input("\nPress Enter to run next file, or type 'q' to quit: ").strip().lower()
        if proceed == 'q':
            print("Stopping execution.")
            break

if __name__ == "__main__":
    folder = "."  # current folder
    run_pxy_files_one_by_one(folder)
