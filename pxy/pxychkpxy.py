import os
import subprocess
import sys

def run_all_sub_scripts():
    # Added your requested exclusions
    exclude_list = [os.path.basename(__file__), "sysexepxy.py","exepxy.py", "sysmonpxy.py", "syspxy.py"]
    failed_scripts = []

    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py') and file not in exclude_list:
                file_path = os.path.abspath(os.path.join(root, file))
                # Get the folder where the script lives
                script_dir = os.path.dirname(file_path)
                
                print(f"\n" + "🚀" * 20)
                print(f"RUNNING: {file_path}")
                print("🚀" * 20)
                
                try:
                    # 'cwd' switches the execution directory to the script's own folder
                    subprocess.run([sys.executable, file_path], check=True, cwd=script_dir)
                    print(f"\n✅ [DONE]: {file}")
                except subprocess.CalledProcessError as e:
                    print(f"\n⚠️ [CRASHED]: {file_path}")
                    failed_scripts.append(f"{file_path} (Exit Code: {e.returncode})")
                    
                    # Manual intervention: wait and ask before moving to next
                    choice = input("\nError detected. Continue to next script? (y/n): ").strip().lower()
                    if choice != 'y':
                        print("🛑 Stopping runner.")
                        sys.exit()

    # Final Summary Report
    print("\n" + "="*40)
    print("🏁 PROCESS COMPLETE")
    if failed_scripts:
        print("\n❌ SCRIPTS WITH ERRORS:")
        for fail in failed_scripts:
            print(f"  - {fail}")
    else:
        print("\n✨ All scripts ran successfully!")
    print("="*40)

if __name__ == "__main__":
    run_all_sub_scripts()



