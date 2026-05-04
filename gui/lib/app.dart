import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'screens/launcher_screen.dart';
import 'state/launcher_state.dart';

class VGALauncherApp extends StatelessWidget {
  const VGALauncherApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) {
        final state = LauncherState();
        // Auto-check environment dependencies on startup
        Future.microtask(() => state.checkDependencies());
        return state;
      },
      child: MaterialApp(
        title: 'Simple VGA Simulator',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
          useMaterial3: true,
        ),
        home: const LauncherScreen(),
      ),
    );
  }
}
