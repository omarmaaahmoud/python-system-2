import os
import subprocess
from pathlib import Path

desktop = Path(os.environ["USERPROFILE"]) / "OneDrive" / "Desktop"
if not desktop.exists():
    desktop = Path(os.environ["USERPROFILE"]) / "Desktop"

target_exe = r"C:\Users\omar mahmoud\.gemini\antigravity-ide\scratch\exclusions_prisoners_system\dist\ExclusionsAndPrisonersSystem\ExclusionsAndPrisonersSystem.exe"
work_dir = r"C:\Users\omar mahmoud\.gemini\antigravity-ide\scratch\exclusions_prisoners_system\dist\ExclusionsAndPrisonersSystem"
icon_file = r"C:\Users\omar mahmoud\.gemini\antigravity-ide\scratch\exclusions_prisoners_system\assets\app_icon.ico"

temp_lnk = desktop / "app_shortcut_temp.lnk"
final_lnk = desktop / "نظام بيانات المستبعدين والمسجونين.lnk"

ps_code = f"""
$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut('{temp_lnk}')
$sc.TargetPath = '{target_exe}'
$sc.WorkingDirectory = '{work_dir}'
$sc.IconLocation = '{icon_file},0'
$sc.Save()
"""

subprocess.run(["powershell", "-Command", ps_code], check=True)

if temp_lnk.exists():
    if final_lnk.exists():
        final_lnk.unlink()
    temp_lnk.rename(final_lnk)
    print("SHORTCUT_CREATED_SUCCESSFULLY:", final_lnk.exists())
else:
    print("FAILED_TEMP_CREATION")
