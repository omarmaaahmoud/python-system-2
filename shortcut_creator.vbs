
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "C:\Users\omar mahmoud\OneDrive\Desktop\نظام بيانات المستبعدين والمسجونين.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "C:\Users\omar mahmoud\.gemini\antigravity-ide\scratch\exclusions_prisoners_system\dist\ExclusionsAndPrisonersSystem\ExclusionsAndPrisonersSystem.exe"
oLink.WorkingDirectory = "C:\Users\omar mahmoud\.gemini\antigravity-ide\scratch\exclusions_prisoners_system\dist\ExclusionsAndPrisonersSystem"
oLink.Description = "نظام بيانات المستبعدين والمسجونين - مديرية التربية والتعليم بالإسكندرية"
oLink.IconLocation = "C:\Users\omar mahmoud\.gemini\antigravity-ide\scratch\exclusions_prisoners_system\dist\ExclusionsAndPrisonersSystem\assets\app_icon.ico,0"
oLink.Save
