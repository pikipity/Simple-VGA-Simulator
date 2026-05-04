import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/dependency.dart';
import '../state/launcher_state.dart';

class DependencyCheckCard extends StatelessWidget {
  const DependencyCheckCard({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<LauncherState>();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.security, size: 20),
                const SizedBox(width: 8),
                const Text(
                  'Step 0: Environment Check',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                if (state.isCheckingDependencies)
                  const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                else
                  TextButton.icon(
                    onPressed: () => state.checkDependencies(),
                    icon: const Icon(Icons.refresh, size: 16),
                    label: const Text('Recheck'),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            if (state.dependencies.isEmpty)
              const Text('Click "Recheck" to verify environment')
            else
              ...state.dependencies.map((dep) {
                final ok = dep.isFullySatisfied;
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    children: [
                      Icon(
                        ok ? Icons.check_circle : Icons.error,
                        color: ok ? Colors.green : Colors.red,
                        size: 18,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text('${dep.name}: ${dep.displayVersion}'),
                      ),
                      if (!ok)
                        Tooltip(
                          message: _getInstallGuide(dep),
                          child: const Icon(Icons.help_outline, size: 16),
                        ),
                    ],
                  ),
                );
              }),
            if (!state.dependenciesSatisfied && state.dependencies.isNotEmpty)
              Container(
                margin: const EdgeInsets.only(top: 8),
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text(
                  'Some dependencies are missing. Please refer to the installation guide for each tool.',
                  style: TextStyle(color: Colors.red, fontSize: 12),
                ),
              ),
          ],
        ),
      ),
    );
  }

  String _getInstallGuide(Dependency dep) {
    if (Platform.isWindows) return dep.installGuideWindows;
    if (Platform.isMacOS) return dep.installGuideMacOS;
    return dep.installGuideUbuntu;
  }
}
