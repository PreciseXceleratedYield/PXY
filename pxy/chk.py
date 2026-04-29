import os
import subprocess
import sys

def run_all_sub_scripts():
    # Get the name of this script to avoid running itself in a loop
    current_script = os.path.basename(__file__)
    
    # Walk through current directory and all subdirectories
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py') and file != current_script:
                file_path = os.path.join(root, file)
                
                print(f"\n" + "="*50)
                print(f"EXECUTING: {file_path}")
                print("="*50)
                
                try:
                    # Run the python file. 'check=True' raises an error if the script fails.
                    subprocess.run([sys.executable, file_path], check=True)
                    print(f"\n[SUCCESS]: {file_path} finished.")
                
                except subprocess.CalledProcessError as e:
                    print(f"\n[ERROR]: {file_path} failed with exit code {e.returncode}")
                    
                    # Pause and ask user for continuation
                    user_input = input("\nScript crashed. Continue to next file? (y/n): ").lower()
                    if user_input != 'y':
                        print("Exiting manager.")
                        return

if __name__ == "__main__":
    run_all_sub_scripts()
