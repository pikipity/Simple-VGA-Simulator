import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as path;
import '../models/dependency.dart';
import '../models/project_config.dart';
import '../models/verilog_module.dart';
import '../services/compiler_service.dart';
import '../services/dependency_checker.dart';
import '../services/verilog_parser.dart';
import '../services/workspace_service.dart';

class LauncherState extends ChangeNotifier {
  // Step 0: Dependencies
  List<Dependency> dependencies = [];
  bool isCheckingDependencies = false;

  // Step 1: Project
  ProjectConfig? project;
  List<VerilogModule> scannedModules = [];
  bool isScanning = false;

  // Step 2: Top Module
  VerilogModule? selectedModule;

  // Step 3: Signal Mapping
  Map<String, String> signalMapping = {};

  // Runtime state
  bool isRunning = false;
  List<String> logLines = [];
  String? errorMessage;

  // Fixed board signal list
  final List<String> boardSignals = [
    'clk', 'reset', 'B2', 'B3', 'B4', 'B5',
    'h_sync', 'v_sync', 'rgb',
    'led1', 'led2', 'led3', 'led4', 'led5',
  ];

  /// Step 0: Check dependencies
  Future<void> checkDependencies() async {
    isCheckingDependencies = true;
    notifyListeners();

    dependencies = await DependencyChecker.checkAll();
    isCheckingDependencies = false;
    notifyListeners();
  }

  /// Step 1: Select project directory
  Future<void> selectProject(String rtlDir) async {
    isScanning = true;
    notifyListeners();

    scannedModules = VerilogParser.scanDirectory(rtlDir);
    final files = scannedModules.map((m) => m.filePath).toSet().toList();

    project = ProjectConfig(
      rtlDirectory: rtlDir,
      verilogFiles: files,
    );
    selectedModule = null;
    signalMapping = {};

    isScanning = false;
    notifyListeners();
  }

  /// Step 2: Select Top Module
  void selectTopModule(String moduleName) {
    selectedModule = scannedModules.firstWhere(
      (m) => m.name == moduleName,
      orElse: () => throw Exception('Module $moduleName does not exist'),
    );
    project = project!.copyWith(topModuleName: moduleName);

    autoInferMapping();
    notifyListeners();
  }

  /// Auto-infer signal mapping
  void autoInferMapping() {
    if (selectedModule == null) return;

    final ports = selectedModule!.ports.map((p) => p.name).toList();
    final mapping = <String, String>{};

    final rules = <String, List<String>>{
      'clk': ['clk', 'sys_clk', 'clock', 'sys_clock'],
      'reset': ['reset', 'sys_rst_n', 'rst_n', 'rst', 'sys_reset'],
      'B2': ['up', 'b2', 'btn2'],
      'B3': ['down', 'b3', 'btn3'],
      'B4': ['left', 'b4', 'btn4'],
      'B5': ['right', 'b5', 'btn5'],
      'h_sync': ['h_sync', 'hsync', 'hs'],
      'v_sync': ['v_sync', 'vsync', 'vs'],
      'rgb': ['rgb', 'vga_rgb', 'data'],
      'led1': ['led1'],
      'led2': ['led2'],
      'led3': ['led3'],
      'led4': ['led4'],
      'led5': ['led5'],
    };

    for (final boardSignal in boardSignals) {
      String? matched;
      final candidates = rules[boardSignal] ?? [];
      for (final candidate in candidates) {
        if (ports.contains(candidate)) {
          matched = candidate;
          break;
        }
      }
      mapping[boardSignal] = matched ?? '';
    }

    signalMapping = mapping;
  }

  void updateMapping(String boardSignal, String moduleSignal) {
    signalMapping = {...signalMapping, boardSignal: moduleSignal};
    notifyListeners();
  }

  /// Run simulation
  Future<void> runSimulation() async {
    if (project == null || selectedModule == null) return;

    final rtlDir = project!.rtlDirectory;
    final simDir = path.join(rtlDir, 'sim');

    // 1. Prepare workspace: create sim/, copy templates, generate DevelopmentBoard.v
    try {
      await WorkspaceService.prepareWorkspace(
        rtlDir: rtlDir,
        moduleName: selectedModule!.name,
        mapping: signalMapping,
      );
    } catch (e) {
      logLines = ['[ERROR] Failed to prepare workspace: $e'];
      notifyListeners();
      return;
    }

    logLines = [
      '[INFO] Workspace prepared: $simDir',
      '[INFO] DevelopmentBoard.v generated',
    ];
    isRunning = true;
    notifyListeners();

    // 2. Start compilation
    File? logSink;
    IOSink? sink;
    try {
      logSink = File(path.join(simDir, 'sim.log'));
      sink = logSink.openWrite(mode: FileMode.append);
      sink.writeln('\n========== ${DateTime.now()} ==========');

      final stream = await CompilerService.startSimulation(
        rtlDir: rtlDir,
        simDir: simDir,
      );

      await for (final line in stream) {
        final trimmed = line.trimRight();
        logLines.add(trimmed);
        sink.writeln(trimmed);

        if (logLines.length > 1000) {
          logLines.removeAt(0);
        }

        notifyListeners();
      }
    } catch (e) {
      logLines.add('[ERROR] $e');
      errorMessage = e.toString();
    } finally {
      await sink?.close();
      isRunning = false;
      notifyListeners();
    }
  }

  Future<void> stopSimulation() async {
    await CompilerService.stopSimulation();
    isRunning = false;
    logLines.add('[INFO] Simulation stopped');
    notifyListeners();
  }

  void clearLogs() {
    logLines = [];
    notifyListeners();
  }

  bool get canRun {
    if (isRunning) return false;
    if (selectedModule == null) return false;
    return signalMapping.values.any((v) => v.isNotEmpty);
  }

  bool get dependenciesSatisfied {
    return dependencies.every((d) => d.isFullySatisfied);
  }
}
