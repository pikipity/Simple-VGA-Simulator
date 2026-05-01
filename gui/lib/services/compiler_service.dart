import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'platform_helper.dart';

class CompilerService {
  static Process? _currentProcess;

  static bool get isRunning => _currentProcess != null;

  static Future<Stream<String>> startSimulation({
    required String rtlDir,
    required String simDir,
  }) async {
    if (_currentProcess != null) {
      throw Exception('已有仿真进程在运行');
    }

    final useWsl = await _shouldUseWsl();
    Process process;

    if (useWsl) {
      final wslRtl = PlatformHelper.toWslPath(rtlDir);
      final wslSim = PlatformHelper.toWslPath(simDir);
      if (wslRtl == null || wslSim == null) {
        throw Exception('无法将 Windows 路径转换为 WSL 路径');
      }
      process = await Process.start('wsl', [
        'bash',
        '-c',
        'cd "$wslSim" && ./run_simulation.sh "$wslRtl"'
      ]);
    } else {
      process = await Process.start(
        'bash',
        ['./run_simulation.sh', rtlDir],
        workingDirectory: simDir,
      );
    }

    _currentProcess = process;

    final stdoutStream = process.stdout.transform(utf8.decoder);
    final stderrStream = process.stderr.transform(utf8.decoder);

    // 合并 stdout 和 stderr
    final controller = StreamController<String>();
    stdoutStream.listen(
      (data) { if (!controller.isClosed) controller.add(data); },
      onError: (e, st) { if (!controller.isClosed) controller.addError(e, st); },
    );
    stderrStream.listen(
      (data) { if (!controller.isClosed) controller.add(data); },
      onError: (e, st) { if (!controller.isClosed) controller.addError(e, st); },
    );

    process.exitCode.then((_) {
      _currentProcess = null;
      if (!controller.isClosed) controller.close();
    });

    return controller.stream;
  }

  static Future<void> stopSimulation() async {
    _currentProcess?.kill();
    _currentProcess = null;
  }

  static Future<bool> _shouldUseWsl() async {
    if (!PlatformHelper.isWindows) return false;

    // 优先检查本机
    try {
      final result = await Process.run('verilator', ['--version']);
      if (result.exitCode == 0) return false;
    } catch (_) {}

    // 本机没有，检查 WSL
    try {
      final result = await Process.run('wsl', ['verilator', '--version']);
      return result.exitCode == 0;
    } catch (_) {
      return false;
    }
  }
}
