import 'package:flutter/material.dart';
import '../widgets/action_area.dart';
import '../widgets/dependency_check_card.dart';
import '../widgets/file_selector_card.dart';
import '../widgets/log_console.dart';
import '../widgets/signal_mapping_card.dart';
import '../widgets/top_module_card.dart';

class LauncherScreen extends StatelessWidget {
  const LauncherScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Simple VGA Simulator'),
        centerTitle: true,
      ),
      body: const SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            DependencyCheckCard(),
            SizedBox(height: 16),
            FileSelectorCard(),
            SizedBox(height: 16),
            TopModuleCard(),
            SizedBox(height: 16),
            SignalMappingCard(),
            SizedBox(height: 16),
            ActionArea(),
            SizedBox(height: 16),
            LogConsole(),
          ],
        ),
      ),
    );
  }
}
