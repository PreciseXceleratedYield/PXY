import os
import subprocess
import sys

def run_all_sub_scripts():
    # Files to ignore (this script itself and exepxy.py)
    exclude_list = [os.path.basename(__file__), "exepxy.py"]
    
    # Walk through current directory and all subdirectories
    for root, dirs, files in os.walk('.'):
        for file in files:
            # Only target .py files not in the exclude list
            if file.endswith('.py') and file not in exclude_list:
                file_path = os.path.join(root, file)
                
                print(f"\n" + "🚀" * 20)
                print(f"RUNNING: {file_path}")
                print("🚀" * 20)
                
                try:
                    # Execute the script
                    subprocess.run([sys.executable, file_path], check=True)
                    print(f"\n✅ [DONE]: {file}")
                
                except subprocess.CalledProcessError as e:
                    print(f"\n⚠️ [CRASHED]: {file_path}")
                    print(f"Error Code: {e.returncode}")
                    
                    # Manual intervention required
                    choice = input("\nError detected. Continue to next script? (y/n): ").strip().lower()
                    if choice != 'y':
                        print("🛑 Stopping runner.")
                        sys.exit()

if __name__ == "__main__":
    run_all_sub_scripts()

