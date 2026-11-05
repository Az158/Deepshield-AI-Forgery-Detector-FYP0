import 'package:flutter/material.dart';

import '../../core/theme.dart';
import '../../data/models/analysis_result.dart';

class VerdictBadge extends StatelessWidget {
  const VerdictBadge({super.key, required this.verdict, this.compact = false});

  final Verdict verdict;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final label = switch (verdict) {
      Verdict.authentic => 'Authentic',
      Verdict.suspected => 'Suspected Manipulation',
      Verdict.inconclusive => 'Inconclusive',
    };

    final color = switch (verdict) {
      Verdict.authentic => Colors.greenAccent,
      Verdict.suspected => Colors.redAccent,
      Verdict.inconclusive => Colors.amberAccent,
    };

    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 10 : 14,
        vertical: compact ? 6 : 9,
      ),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            color.withOpacity(0.18),
            color.withOpacity(0.06),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(compact ? 18 : 22),
        border: Border.all(color: color.withOpacity(0.5)),
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(0.18),
            blurRadius: 10,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.verified_rounded, color: color, size: compact ? 16 : 18),
          const SizedBox(width: 6),
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w700,
                ),
          ),
        ],
      ),
    );
  }
}
