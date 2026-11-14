import os
import subprocess
from pathlib import Path

base = Path(__file__).resolve().parent
out_folder = base / "dist" / "ExclusionsAndPrisonersSystem"
exe_path = out_folder / "ExclusionsAndPrisonersSystem.exe"
icon_path = out_folder / "assets" / "app_icon.ico"

desktops = [
    Path(os.environ.get("USERPROFILE", "")) / "OneDrive" / "Desktop",
    Path(os.environ.get("USERPROFILE", "")) / "Desktop",
]

vbs_file = base / "shortcut_creator.vbs"

for dt in desktops:
    if dt.exists():
        shortcut_file = dt / "نظام بيانات المستبعدين والمسجونين.lnk"
        vbs_content = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_file}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{exe_path}"
oLink.WorkingDirectory = "{out_folder}"
oLink.Description = "نظام بيانات المستبعدين والمسجونين - مديرية التربية والتعليم بالإسكندرية"
oLink.IconLocation = "{icon_path},0"
oLink.Save
"""
        vbs_file.write_text(vbs_content, encoding="utf-8")
        subprocess.run(["cscript", "//nologo", str(vbs_file)], check=True)
        print(f"Shortcut created successfully at: {shortcut_file}")

vbs_file.unlink(missing_ok=True)
print("Finished!")
