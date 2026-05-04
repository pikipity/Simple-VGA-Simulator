class Dependency {
  final String name;
  final String command;
  final List<String> versionArgs;
  final String? minVersion;
  final String installGuideUbuntu;
  final String installGuideMacOS;
  final String installGuideWindows;

  bool isInstalled;
  String? version;
  bool wslAvailable;
  String? wslVersion;
  String? errorMessage;

  Dependency({
    required this.name,
    required this.command,
    this.versionArgs = const ['--version'],
    this.minVersion,
    required this.installGuideUbuntu,
    required this.installGuideMacOS,
    required this.installGuideWindows,
    this.isInstalled = false,
    this.version,
    this.wslAvailable = false,
    this.wslVersion,
    this.errorMessage,
  });

  bool get isFullySatisfied => isInstalled || wslAvailable;

  String get displayVersion {
    if (isInstalled && version != null) return version!;
    if (wslAvailable && wslVersion != null) return '$wslVersion (WSL)';
    return 'Not Installed';
  }
}
