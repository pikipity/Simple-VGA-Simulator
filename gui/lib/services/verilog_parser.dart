import 'dart:io';
import '../models/verilog_module.dart';

class VerilogParser {
  static List<VerilogModule> scanDirectory(String dirPath) {
    final dir = Directory(dirPath);
    if (!dir.existsSync()) return [];

    final modules = <VerilogModule>[];
    final files = dir
        .listSync()
        .whereType<File>()
        .where((f) => f.path.toLowerCase().endsWith('.v'));

    for (final file in files) {
      try {
        final content = file.readAsStringSync();
        final fileModules = _parseContent(content, file.path);
        modules.addAll(fileModules);
      } catch (_) {
        // 忽略无法解析的文件
      }
    }
    return modules;
  }

  static List<VerilogModule> _parseContent(String content, String filePath) {
    final modules = <VerilogModule>[];

    // 移除行注释
    content = content.replaceAll(RegExp(r'//.*'), '');
    // 移除块注释
    content = content.replaceAllMapped(
      RegExp(r'/\*.*?\*/', dotAll: true),
      (m) => '',
    );

    // 匹配 module 声明 (ANSI 风格)
    final moduleRegex = RegExp(
      r'module\s+(\w+)\s*\(([^)]*)\)',
      dotAll: true,
    );

    for (final match in moduleRegex.allMatches(content)) {
      final name = match.group(1)!;
      final portSection = match.group(2)!;
      final ports = _parsePorts(portSection);
      modules.add(VerilogModule(
        name: name,
        filePath: filePath,
        ports: ports,
      ));
    }

    return modules;
  }

  static List<ModulePort> _parsePorts(String portSection) {
    final ports = <ModulePort>[];
    final rawItems = portSection.split(',');

    for (var item in rawItems) {
      item = item.trim();
      if (item.isEmpty) continue;

      final port = _extractPort(item);
      if (port != null) ports.add(port);
    }

    return ports;
  }

  static ModulePort? _extractPort(String decl) {
    decl = decl.trim();
    if (decl.isEmpty) return null;

    // 提取方向
    final dirMatch = RegExp(
      r'^(input|output|inout)\b',
      caseSensitive: false,
    ).firstMatch(decl);
    if (dirMatch == null) return null;

    final direction = dirMatch.group(1)!.toLowerCase();
    decl = decl.substring(dirMatch.end).trim();

    // 提取类型 (wire/reg)
    String? type;
    final typeMatch = RegExp(
      r'^(wire|reg)\b',
      caseSensitive: false,
    ).firstMatch(decl);
    if (typeMatch != null) {
      type = typeMatch.group(1)!.toLowerCase();
      decl = decl.substring(typeMatch.end).trim();
    }

    // 提取位宽
    String? bitwidth;
    final bitMatch = RegExp(r'^(\[[^\]]+\])').firstMatch(decl);
    if (bitMatch != null) {
      bitwidth = bitMatch.group(1);
      decl = decl.substring(bitMatch.end).trim();
    }

    // 提取信号名
    decl = decl.replaceAll(',', '').trim();
    if (!RegExp(r'^[a-zA-Z_][a-zA-Z0-9_]*$').hasMatch(decl)) {
      return null;
    }

    return ModulePort(
      direction: direction,
      type: type,
      bitwidth: bitwidth,
      name: decl,
    );
  }
}
