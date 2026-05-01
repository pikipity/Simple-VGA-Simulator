class ProjectConfig {
  final String rtlDirectory;
  final String? topModuleName;
  final Map<String, String> signalMapping;
  final List<String> verilogFiles;

  ProjectConfig({
    required this.rtlDirectory,
    this.topModuleName,
    this.signalMapping = const {},
    this.verilogFiles = const [],
  });

  ProjectConfig copyWith({
    String? rtlDirectory,
    String? topModuleName,
    Map<String, String>? signalMapping,
    List<String>? verilogFiles,
  }) {
    return ProjectConfig(
      rtlDirectory: rtlDirectory ?? this.rtlDirectory,
      topModuleName: topModuleName ?? this.topModuleName,
      signalMapping: signalMapping ?? this.signalMapping,
      verilogFiles: verilogFiles ?? this.verilogFiles,
    );
  }
}
