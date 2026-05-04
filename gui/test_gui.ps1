#Requires -Version 5.1
$ErrorActionPreference = "Stop"

# Script directory (i.e., gui/ directory)
$sourceDir = $PSScriptRoot
$proxyDir  = "C:\Windows\Temp\vga_gui_test"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VGA GUI Windows Build Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Source: $sourceDir"
Write-Host "Proxy:  $proxyDir"
Write-Host ""

# ============ Smart Detection: Can proxy directory be reused? ============

$needRebuild = $false

if (Test-Path $proxyDir) {
    Write-Host "Proxy directory found. Checking validity..."
    
    # Check 1: Is pubspec.yaml up-to-date?
    $pubspecSource = Get-Item "$sourceDir\pubspec.yaml"
    $pubspecProxy  = Get-Item "$proxyDir\pubspec.yaml" -ErrorAction SilentlyContinue
    $pubspecOk = $pubspecProxy -and ($pubspecProxy.LastWriteTime -ge $pubspecSource.LastWriteTime)
    Write-Host "  pubspec.yaml up-to-date : $pubspecOk"
    
    # Check 2: Are Junction links valid?
    $junctionOk = Test-Path "$proxyDir\lib\services\workspace_service.dart"
    Write-Host "  Junction links valid    : $junctionOk"
    
    # Check 3: Does Windows platform directory exist?
    $windowsOk = Test-Path "$proxyDir\windows\runner"
    Write-Host "  windows platform ready  : $windowsOk"
    
    if ($pubspecOk -and $junctionOk -and $windowsOk) {
        Write-Host ""
        Write-Host "All checks passed. Skipping setup, building directly..." -ForegroundColor Green
        Set-Location $proxyDir
        flutter build windows
        if ($LASTEXITCODE -eq 0) {
            $exe = Get-ChildItem "$proxyDir\build\windows\x64\runner\Release\*.exe" | Select-Object -First 1
            if ($exe) {
                Write-Host ""
                Write-Host "Launching application..." -ForegroundColor Cyan
                Start-Process $exe.FullName
            }
        }
        Set-Location $sourceDir
        return
    } else {
        Write-Host ""
        Write-Host "Some checks failed. Rebuilding proxy directory..." -ForegroundColor Yellow
        $needRebuild = $true
    }
} else {
    $needRebuild = $true
}

# ============ Full Rebuild Logic ============

if ($needRebuild) {
    # 1. Clean up
    if (Test-Path $proxyDir) {
        Write-Host "[1/5] Cleaning old proxy directory..."
        Remove-Item -Recurse -Force $proxyDir
    }
    
    # 2. Create directory
    Write-Host "[2/5] Creating proxy directory..."
    New-Item -ItemType Directory -Path $proxyDir -Force | Out-Null
    
    # 3. Copy config files
    Write-Host "[3/5] Copying config files..."
    Copy-Item "$sourceDir\pubspec.yaml" "$proxyDir\"
    Copy-Item "$sourceDir\analysis_options.yaml" "$proxyDir\"
    
    # 4. Create Junction links
    Write-Host "[4/5] Creating Junction links..."
    cmd /c mklink /J "$proxyDir\lib" "$sourceDir\lib" | Out-Null
    cmd /c mklink /J "$proxyDir\assets" "$sourceDir\assets" | Out-Null
    
    # 5. Flutter create
    Write-Host "[5/5] Running flutter create --platforms=windows ..."
    Set-Location $proxyDir
    flutter create --platforms=windows . 2>&1 | ForEach-Object { Write-Host "  $_" }
}

# ============ Compile ============

Write-Host ""
Write-Host "Building Windows executable..."
flutter build windows 2>&1 | ForEach-Object { Write-Host "  $_" }

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Build Successful!" -ForegroundColor Green
    $exe = Get-ChildItem "$proxyDir\build\windows\x64\runner\Release\*.exe" | Select-Object -First 1
    if ($exe) { 
        Write-Host "  $($exe.FullName)" -ForegroundColor Green
        Write-Host ""
        Write-Host "Launching application..." -ForegroundColor Cyan
        Start-Process $exe.FullName
    }
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  Build Failed!" -ForegroundColor Red
}

Set-Location $sourceDir
