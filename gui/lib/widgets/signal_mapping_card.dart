import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../state/launcher_state.dart';

class SignalMappingCard extends StatelessWidget {
  const SignalMappingCard({super.key});

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
                const Icon(Icons.cable, size: 20),
                const SizedBox(width: 8),
                const Text(
                  'Step 3: 信号映射',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                if (state.selectedModule != null)
                  TextButton.icon(
                    onPressed: () => state.autoInferMapping(),
                    icon: const Icon(Icons.auto_fix_high, size: 16),
                    label: const Text('自动推断'),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            if (state.selectedModule == null)
              const Text(
                '请先选择 Top Module',
                style: TextStyle(color: Colors.grey),
              )
            else
              Table(
                columnWidths: const {
                  0: FixedColumnWidth(100),
                  1: FixedColumnWidth(40),
                  2: FlexColumnWidth(),
                },
                defaultVerticalAlignment: TableCellVerticalAlignment.middle,
                children: [
                  const TableRow(
                    children: [
                      Padding(
                        padding: EdgeInsets.symmetric(vertical: 4),
                        child: Text('开发板信号',
                            style: TextStyle(fontWeight: FontWeight.bold)),
                      ),
                      SizedBox(),
                      Text('模块信号',
                          style: TextStyle(fontWeight: FontWeight.bold)),
                    ],
                  ),
                  ...state.boardSignals.map((boardSignal) {
                    final modulePorts = [
                      '(未连接)',
                      ...state.selectedModule!.ports.map((p) => p.name)
                    ];
                    final currentValue = state.signalMapping[boardSignal] ?? '';
                    final selectedValue =
                        modulePorts.contains(currentValue) && currentValue.isNotEmpty
                            ? currentValue
                            : '(未连接)';

                    return TableRow(
                      children: [
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Text(boardSignal),
                        ),
                        const Center(child: Text('=>')),
                        DropdownButtonFormField<String>(
                          value: selectedValue,
                          isDense: true,
                          items: modulePorts.map((port) {
                            return DropdownMenuItem(
                              value: port,
                              child:
                                  Text(port, style: const TextStyle(fontSize: 13)),
                            );
                          }).toList(),
                          onChanged: (value) {
                            if (value != null) {
                              state.updateMapping(
                                boardSignal,
                                value == '(未连接)' ? '' : value,
                              );
                            }
                          },
                        ),
                      ],
                    );
                  }),
                ],
              ),
          ],
        ),
      ),
    );
  }
}
