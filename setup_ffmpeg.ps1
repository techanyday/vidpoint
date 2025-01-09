# Create tools directory if it doesn't exist
$toolsDir = "C:\tools"
if (-not (Test-Path $toolsDir)) {
    New-Item -ItemType Directory -Path $toolsDir
}

# Download FFmpeg
$ffmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
$ffmpegZip = "$toolsDir\ffmpeg.zip"
Invoke-WebRequest -Uri $ffmpegUrl -OutFile $ffmpegZip

# Extract FFmpeg
Expand-Archive -Path $ffmpegZip -DestinationPath $toolsDir -Force
$ffmpegDir = Get-ChildItem -Path $toolsDir -Filter "ffmpeg-*-essentials_build" | Select-Object -First 1
Rename-Item -Path $ffmpegDir.FullName -NewName "ffmpeg"

# Add to PATH
$ffmpegPath = "$toolsDir\ffmpeg\bin"
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$ffmpegPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$ffmpegPath", "User")
}
