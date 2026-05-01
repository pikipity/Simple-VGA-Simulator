import 'dart:io';
import 'package:flutter/services.dart';
import 'package:path/path.dart' as path;
import 'board_generator.dart';
import 'platform_helper.dart';

/// 负责创建和管理 <RTL>/sim/ 工作目录
class WorkspaceService {
  /// 准备仿真工作目录
  /// 返回 simDir 路径
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

    // 1. 复制 simulator.cpp
    final simCpp = await rootBundle.loadString('assets/sim/simulator.cpp');
    await File(path.join(simDir, 'simulator.cpp')).writeAsString(simCpp);

    // 2. 复制 run_simulation.sh（确保 LF 行尾）
    final simShRaw = await rootBundle.loadString('assets/sim/run_simulation.sh');
    final simSh = simShRaw.replaceAll('\r\n', '\n');
    final shFile = File(path.join(simDir, 'run_simulation.sh'));
    await shFile.writeAsString(simSh);

    // 设置可执行权限（非 Windows）
    if (!PlatformHelper.isWindows) {
      await Process.run('chmod', ['+x', shFile.path]);
    }

    // 3. 生成 DevelopmentBoard.v
    await BoardGenerator.generate(
      outputPath: path.join(simDir, 'DevelopmentBoard.v'),
      moduleName: moduleName,
      mapping: mapping,
    );

    return simDir;
  }
}
