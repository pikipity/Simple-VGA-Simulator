import 'dart:io';
import 'package:flutter/services.dart';
import 'package:path/path.dart' as path;
import 'board_generator.dart';
import 'platform_helper.dart';

/// Responsible for creating and managing the <RTL>/sim/ workspace
class WorkspaceService {
  /// Prepare simulation workspace
  /// Returns the simDir path
  static Future<String> prepareWorkspace({
    required String rtlDir,
    required String moduleName,
    required Map<String, String> mapping,
  }) async {
    final simDir = path.join(rtlDir, 'sim');
    final dir = Directory(simDir);
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }

    // 1. Copy simulator.cpp
    final simCpp = await rootBundle.loadString('assets/sim/simulator.cpp');
    await File(path.join(simDir, 'simulator.cpp')).writeAsString(simCpp);

    // 2. Copy run_simulation.sh (ensure LF line endings)
    final simShRaw = await rootBundle.loadString('assets/sim/run_simulation.sh');
    final simSh = simShRaw.replaceAll('\r\n', '\n');
    final shFile = File(path.join(simDir, 'run_simulation.sh'));
    await shFile.writeAsString(simSh);

    // Set executable permission (non-Windows)
    if (!PlatformHelper.isWindows) {
      await Process.run('chmod', ['+x', shFile.path]);
    }

    // 3. Generate DevelopmentBoard.v
    await BoardGenerator.generate(
      outputPath: path.join(simDir, 'DevelopmentBoard.v'),
      moduleName: moduleName,
      mapping: mapping,
    );

    return simDir;
  }
}
