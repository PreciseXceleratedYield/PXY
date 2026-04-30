import os
import subprocess
import sys

def run_all_sub_scripts():
    exclude_list = [os.path.basename(__file__), "exepxy.py", "sysmonpxy.py", "syspxy.py"]
    results = {"success": [], "errors": []}

    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py') and file not in exclude_list:
                file_path = os.path.join(root, file)
                
                print(f"🚀 RUNNING: {file_path}...")
                
                try:
                    # check=True will raise the exception if the script fails
                    subprocess.run([sys.executable, file_path], check=True, capture_output=True, text=True)
                    results["success"].append(file_path)
                except subprocess.CalledProcessError as e:
                    # Capture error and move to next script without asking
                    error_msg = e.stderr.strip() if e.stderr else "Unknown error"
                    results["errors"].append((file_path, e.returncode, error_msg))
                    print(f"⚠️  FAILED: {file_path}")

    # Final Summary Output
    print("\n" + "="*30)
    print("       FINAL REPORT")
    print("="*30)
    print(f"✅ Completed: {len(results['success'])}")
    print(f"❌ Failed:    {len(results['errors'])}")
    
    if results["errors"]:
        print("\n--- ERROR DETAILS ---")
        for path, code, msg in results["errors"]:
            print(f"\n[!] {path} (Code: {code})")
            # Print last line of error for brevity
            print(f"    Trace: {msg.splitlines()[-1] if msg else 'No stderr'}")
    
    print("\n" + "="*30)

if __name__ == "__main__":
    run_all_sub_scripts()



