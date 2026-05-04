import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../state/launcher_state.dart';

class LogConsole extends StatefulWidget {
  const LogConsole({super.key});

  @override
  State<LogConsole> createState() => _LogConsoleState();
}

class _LogConsoleState extends State<LogConsole> {
  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<LauncherState>();

    // Auto-scroll to bottom
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.jumpTo(
          _scrollController.position.maxScrollExtent,
        );
      }
    });

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.terminal, size: 20),
                const SizedBox(width: 8),
                const Text(
                  'Run Log',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                TextButton.icon(
                  onPressed: state.logLines.isNotEmpty
                      ? () => state.clearLogs()
                      : null,
                  icon: const Icon(Icons.clear_all, size: 16),
                  label: const Text('Clear'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Container(
              height: 240,
              decoration: BoxDecoration(
                color: Colors.grey.shade900,
                borderRadius: BorderRadius.circular(4),
              ),
              child: state.logLines.isEmpty
                  ? const Center(
                      child: Text(
                        'Logs will appear here',
                        style: TextStyle(color: Colors.grey, fontSize: 12),
                      ),
                    )
                  : ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.all(8),
                      itemCount: state.logLines.length,
                      itemBuilder: (context, index) {
                        final line = state.logLines[index];
                        Color color = Colors.grey.shade300;
                        if (line.contains('[ERROR]')) {
                          color = Colors.red.shade300;
                        } else if (line.contains('[WARNING]')) {
                          color = Colors.orange.shade300;
                        } else if (line.contains('[OK]')) {
                          color = Colors.green.shade300;
                        } else if (line.contains('[INFO]')) {
                          color = Colors.blue.shade300;
                        }

                        return SelectableText(
                          line,
                          style: TextStyle(
                            color: color,
                            fontSize: 12,
                            fontFamily: 'monospace',
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
