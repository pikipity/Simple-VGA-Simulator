import 'dart:io';
import 'package:flutter/services.dart';

class BoardGenerator {
  static Future<void> generate({
    required String outputPath,
    required String moduleName,
    required Map<String, String> mapping,
  }) async {
    final template = await rootBundle.loadString(
      'assets/templates/development_board.v.tpl',
    );

    final connections = <String>[];
    for (final entry in mapping.entries) {
      if (entry.value.isNotEmpty) {
        connections.add('    .${entry.value}(${entry.key})');
      }
    }

    final content = template
        .replaceAll('{{module_name}}', moduleName)
        .replaceAll('{{connections}}', connections.join(',\n'));

    final file = File(outputPath);
    await file.writeAsString(content);
  }
}
