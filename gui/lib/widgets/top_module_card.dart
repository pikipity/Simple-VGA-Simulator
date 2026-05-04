import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../state/launcher_state.dart';

class TopModuleCard extends StatelessWidget {
  const TopModuleCard({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<LauncherState>();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.account_tree, size: 20),
                SizedBox(width: 8),
                Text(
                  'Step 2: Specify Top Module',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (state.scannedModules.isEmpty)
              const Text(
                'Please select a project directory first',
                style: TextStyle(color: Colors.grey),
              )
            else
              DropdownButtonFormField<String>(
                value: state.selectedModule?.name,
                hint: const Text('Select Top Module'),
                items: state.scannedModules.map((m) {
                  final fileName = m.filePath.split('\\').last.split('/').last;
                  return DropdownMenuItem(
                    value: m.name,
                    child: Text('$fileName - ${m.name}'),
                  );
                }).toList(),
                onChanged: (value) {
                  if (value != null) state.selectTopModule(value);
                },
              ),
            if (state.selectedModule != null) ...[
              const SizedBox(height: 12),
              const Text(
                'Module Ports:',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: state.selectedModule!.ports.map((p) {
                    return Text(
                      '${p.direction} ${p.type ?? ''} ${p.bitwidth ?? ''} ${p.name}',
                      style: const TextStyle(
                        fontSize: 12,
                        fontFamily: 'monospace',
                      ),
                    );
                  }).toList(),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
