import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../state/launcher_state.dart';

class FileSelectorCard extends StatelessWidget {
  const FileSelectorCard({super.key});

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
                Icon(Icons.folder_open, size: 20),
                SizedBox(width: 8),
                Text(
                  'Step 1: Select Project Directory',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    state.project?.rtlDirectory ?? 'Not selected',
                    style: TextStyle(
                      color: state.project == null ? Colors.grey : Colors.black,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                ElevatedButton.icon(
                  onPressed: () async {
                    final result = await FilePicker.platform.getDirectoryPath();
                    if (result != null) {
                      await state.selectProject(result);
                    }
                  },
                  icon: const Icon(Icons.folder_open, size: 16),
                  label: const Text('Browse...'),
                ),
              ],
            ),
            if (state.isScanning)
              const Padding(
                padding: EdgeInsets.only(top: 12),
                child: LinearProgressIndicator(),
              )
            else if (state.scannedModules.isNotEmpty) ...[
              const SizedBox(height: 12),
              const Text(
                'Detected Verilog files:',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
              ),
              const SizedBox(height: 4),
              Wrap(
                spacing: 8,
                children: state.project!.verilogFiles.map((f) {
                  final name = f.split('\\').last.split('/').last;
                  return Chip(
                    label: Text(name, style: const TextStyle(fontSize: 12)),
                    padding: EdgeInsets.zero,
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  );
                }).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
