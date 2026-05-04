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
      throw Exception('A simulation process is already running');
    }

    final useWsl = await _shouldUseWsl();
    Process process;

    if (useWsl) {
      final wslRtl = PlatformHelper.toWslPath(rtlDir);
      final wslSim = PlatformHelper.toWslPath(simDir);
      if (wslRtl == null || wslSim == null) {
        throw Exception('Unable to convert Windows path to WSL path');
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

    // Merge stdout and stderr
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

    // Check native installation first
    try {
      final result = await Process.run('verilator', ['--version']);
      if (result.exitCode == 0) return false;
    } catch (_) {}

    // Native not found, check WSL fallback
    try {
      final result = await Process.run('wsl', ['verilator', '--version']);
      return result.exitCode == 0;
    } catch (_) {
      return false;
    }
  }
}
