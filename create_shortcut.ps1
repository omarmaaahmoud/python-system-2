$targetExe = "C:\Users\omar mahmoud\.gemini\antigravity-ide\scratch\exclusions_prisoners_system\dist\ExclusionsAndPrisonersSystem\ExclusionsAndPrisonersSystem.exe"
$workDir = "C:\Users\omar mahmoud\.gemini\antigravity-ide\scratch\exclusions_prisoners_system\dist\ExclusionsAndPrisonersSystem"
$iconFile = "C:\Users\omar mahmoud\.gemini\antigravity-ide\scratch\exclusions_prisoners_system\assets\app_icon.ico"

$desktop = [Environment]::GetFolderPath("Desktop")

$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut("$desktop\نظام بيانات المستبعدين والمسجونين.lnk")
$sc.TargetPath = $targetExe
$sc.WorkingDirectory = $workDir
$sc.IconLocation = "$iconFile,0"
$sc.Description = "نظام بيانات المستبعدين والمسجونين"
$sc.Save()

Write-Output "SUCCESS"
