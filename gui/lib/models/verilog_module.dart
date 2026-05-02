class VerilogModule {
  final String name;
  final String filePath;
  final List<ModulePort> ports;

  VerilogModule({
    required this.name,
    required this.filePath,
    required this.ports,
  });
}

class ModulePort {
  final String direction; // input, output, inout
  final String? type;     // wire, reg
  final String? bitwidth;
  final String name;

  ModulePort({
    required this.direction,
    this.type,
    this.bitwidth,
    required this.name,
  });

  String get declaration {
    final buffer = StringBuffer();
    buffer.write(direction);
    if (type != null) buffer.write(' $type');
    if (bitwidth != null) buffer.write(' $bitwidth');
    buffer.write(' $name');
    return buffer.toString();
  }
}
