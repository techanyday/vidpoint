# Download MongoDB installer
$mongoUrl = "https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-7.0.4-signed.msi"
$installerPath = "$env:TEMP\mongodb.msi"
Invoke-WebRequest -Uri $mongoUrl -OutFile $installerPath

# Create data directories
$dataPath = "C:\Users\Kwamena\CascadeProjects\WordPilot\Server\data\db"
$logPath = "C:\Users\Kwamena\CascadeProjects\WordPilot\Server\data\log"
New-Item -ItemType Directory -Force -Path $dataPath
New-Item -ItemType Directory -Force -Path $logPath

# Install MongoDB
Start-Process msiexec.exe -Wait -ArgumentList "/i $installerPath ADDLOCAL=ALL"

# Clean up
Remove-Item $installerPath
