# Download Python 3.11
$pythonUrl = "https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe"
$installerPath = "$env:TEMP\python311.exe"
Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath

# Install Python 3.11 (with pip, add to PATH)
Start-Process -Wait -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0"

# Clean up
Remove-Item $installerPath
