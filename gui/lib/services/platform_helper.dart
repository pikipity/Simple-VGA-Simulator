import 'dart:io';

class PlatformHelper {
  static bool get isWindows => Platform.isWindows;
  static bool get isMacOS => Platform.isMacOS;
  static bool get isLinux => Platform.isLinux;

  static String normalizePath(String path) {
    if (isWindows) {
      return path.replaceAll('/', '\\');
    }
    return path;
  }

  /// Convert Windows path to WSL path
  /// e.g. "C:\Users\student\project" -> "/mnt/c/Users/student/project"
  static String? toWslPath(String windowsPath) {
    if (!isWindows) return windowsPath;
    final match = RegExp(r'^([A-Za-z]):\\(.*)$').firstMatch(windowsPath);
    if (match == null) return null;
    final drive = match.group(1)!.toLowerCase();
    final rest = match.group(2)!.replaceAll('\\', '/');
    return '/mnt/$drive/$rest';
  }
}
