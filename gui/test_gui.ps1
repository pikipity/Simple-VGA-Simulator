#Requires -Version 5.1
$ErrorActionPreference = "Stop"

# 脚本所在目录（即 gui/ 目录）
$sourceDir = $PSScriptRoot
$proxyDir  = "C:\Windows\Temp\vga_gui_test"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VGA GUI Windows Build Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Source: $sourceDir"
Write-Host "Proxy:  $proxyDir"
Write-Host ""

# ============ 智能检测：代理目录能否复用 ============

$needRebuild = $false

if (Test-Path $proxyDir) {
    Write-Host "Proxy directory found. Checking validity..."
    
    # 检查 1：pubspec.yaml 是否最新
    $pubspecSource = Get-Item "$sourceDir\pubspec.yaml"
    $pubspecProxy  = Get-Item "$proxyDir\pubspec.yaml" -ErrorAction SilentlyContinue
    $pubspecOk = $pubspecProxy -and ($pubspecProxy.LastWriteTime -ge $pubspecSource.LastWriteTime)
    Write-Host "  pubspec.yaml up-to-date : $pubspecOk"
    
    # 检查 2：Junction 链接是否有效
    $junctionOk = Test-Path "$proxyDir\lib\services\workspace_service.dart"
    Write-Host "  Junction links valid    : $junctionOk"
    
    # 检查 3：windows 平台目录是否存在
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

# ============ 完整重建逻辑 ============

if ($needRebuild) {
    # 1. 清理
    if (Test-Path $proxyDir) {
        Write-Host "[1/5] Cleaning old proxy directory..."
        Remove-Item -Recurse -Force $proxyDir
    }
    
    # 2. 创建目录
    Write-Host "[2/5] Creating proxy directory..."
    New-Item -ItemType Directory -Path $proxyDir -Force | Out-Null
    
    # 3. 复制配置文件
    Write-Host "[3/5] Copying config files..."
    Copy-Item "$sourceDir\pubspec.yaml" "$proxyDir\"
    Copy-Item "$sourceDir\analysis_options.yaml" "$proxyDir\"
    
    # 4. 创建 Junction 链接
    Write-Host "[4/5] Creating Junction links..."
    cmd /c mklink /J "$proxyDir\lib" "$sourceDir\lib" | Out-Null
    cmd /c mklink /J "$proxyDir\assets" "$sourceDir\assets" | Out-Null
    
    # 5. Flutter create
    Write-Host "[5/5] Running flutter create --platforms=windows ..."
    Set-Location $proxyDir
    flutter create --platforms=windows . 2>&1 | ForEach-Object { Write-Host "  $_" }
}

# ============ 编译 ============

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
