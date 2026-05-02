import 'dart:io';
import '../models/dependency.dart';
import 'platform_helper.dart';

class DependencyChecker {
  static final List<Dependency> _base = [
    Dependency(
      name: 'Verilator',
      command: 'verilator',
      versionArgs: const ['--version'],
      minVersion: '4.0',
      installGuideUbuntu: 'sudo apt install verilator',
      installGuideMacOS: 'brew install verilator',
      installGuideWindows: '安装 MSYS2 后执行: pacman -S verilator',
    ),
    Dependency(
      name: 'SDL2',
      command: 'sdl2-config',
      versionArgs: const ['--version'],
      installGuideUbuntu: 'sudo apt install libsdl2-dev',
      installGuideMacOS: 'brew install sdl2',
      installGuideWindows: '安装 MSYS2 后执行: pacman -S mingw-w64-x86_64-SDL2',
    ),
    Dependency(
      name: 'make',
      command: 'make',
      versionArgs: const ['--version'],
      installGuideUbuntu: 'sudo apt install build-essential',
      installGuideMacOS: 'xcode-select --install',
      installGuideWindows: '安装 MSYS2 后执行: pacman -S make',
    ),
    Dependency(
      name: 'g++',
      command: 'g++',
      versionArgs: const ['--version'],
      installGuideUbuntu: 'sudo apt install build-essential',
      installGuideMacOS: 'xcode-select --install',
      installGuideWindows: '安装 MSYS2 后执行: pacman -S mingw-w64-x86_64-gcc',
    ),
  ];

  static Future<List<Dependency>> checkAll() async {
    final futures = _base.map((b) => _checkOne(b));
    return Future.wait(futures);
  }

  static Future<Dependency> _checkOne(Dependency base) async {
    final dep = Dependency(
      name: base.name,
      command: base.command,
      versionArgs: base.versionArgs,
      minVersion: base.minVersion,
      installGuideUbuntu: base.installGuideUbuntu,
      installGuideMacOS: base.installGuideMacOS,
      installGuideWindows: base.installGuideWindows,
    );

    // 1. 检查本机
    final native = await _tryRun(dep.command, dep.versionArgs);
    if (native != null) {
      dep.isInstalled = true;
      dep.version = native;
      return dep;
    }

    // 2. Windows 检查 WSL fallback
    if (PlatformHelper.isWindows) {
      final wsl = await _tryRunInWsl(dep.command, dep.versionArgs);
      if (wsl != null) {
        dep.wslAvailable = true;
        dep.wslVersion = wsl;
        return dep;
      }
    }

    return dep;
  }

  static Future<String?> _tryRun(String cmd, List<String> args) async {
    try {
      final result = await Process.run(cmd, args);
      if (result.exitCode == 0) {
        return _extractVersion(result.stdout.toString());
      }
    } catch (_) {}
    return null;
  }

  static Future<String?> _tryRunInWsl(String cmd, List<String> args) async {
    try {
      // 先确认 WSL 可用
      final wslCheck = await Process.run('wsl', ['echo', 'ok']);
      if (wslCheck.exitCode != 0) return null;

      // 检查 WSL 中命令是否存在
      final whichResult = await Process.run('wsl', ['which', cmd]);
      if (whichResult.exitCode != 0) return null;

      // 获取版本
      final result = await Process.run('wsl', [cmd, ...args]);
      if (result.exitCode == 0) {
        return _extractVersion(result.stdout.toString());
      }
    } catch (_) {}
    return null;
  }

  static String? _extractVersion(String output) {
    final match = RegExp(r'(\d+\.\d+(\.\d+)?)').firstMatch(output);
    return match?.group(1);
  }
}
