# Create directory for FFmpeg
$ffmpegDir = "C:\ffmpeg"
if (-not (Test-Path $ffmpegDir)) {
    New-Item -ItemType Directory -Path $ffmpegDir
}

# Add to PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$ffmpegDir\bin*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$ffmpegDir\bin", "User")
}

Write-Host "Please extract the downloaded FFmpeg zip file to C:\ffmpeg"
Write-Host "Make sure the bin folder is directly under C:\ffmpeg"
