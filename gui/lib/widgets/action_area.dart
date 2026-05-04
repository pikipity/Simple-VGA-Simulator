import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../state/launcher_state.dart';

class ActionArea extends StatelessWidget {
  const ActionArea({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<LauncherState>();

    return Row(
      children: [
        Expanded(
          child: ElevatedButton.icon(
            onPressed: state.canRun ? () => state.runSimulation() : null,
            icon: state.isRunning
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.play_arrow),
            label: Text(state.isRunning ? 'Running...' : '🚀 Run Simulation'),
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
              textStyle: const TextStyle(fontSize: 16),
            ),
          ),
        ),
        if (state.isRunning) ...[
          const SizedBox(width: 12),
          ElevatedButton.icon(
            onPressed: () => state.stopSimulation(),
            icon: const Icon(Icons.stop),
            label: const Text('Stop'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
          ),
        ],
      ],
    );
  }
}
