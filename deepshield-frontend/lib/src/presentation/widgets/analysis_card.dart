import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/constants.dart';
import '../../core/theme.dart';
import '../../data/models/analysis_result.dart';
import 'verdict_badge.dart';
import 'media_preview.dart';

class AnalysisCard extends StatelessWidget {
  const AnalysisCard({
    super.key,
    required this.result,
    required this.onTap,
  });

  final AnalysisResult result;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final formatter = DateFormat('MMM d, h:mm a');
    return InkWell(
      onTap: onTap,
      borderRadius: AppRadii.card,
      child: Ink(
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: AppColors.cardOverlay,
          borderRadius: AppRadii.card,
          boxShadow: const [AppShadows.soft],
          border: Border.all(color: AppColors.subtle),
        ),
        child: Row(
          children: [
            const SizedBox(width: AppSpacing.sm),
            SizedBox(
              width: 72,
              child: MediaPreview(
                thumbnailAsset: result.mediaItem.thumbnailAsset,
                title: null,
                subtitle: null,
                compact: true,
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    result.mediaTitle,
                    style: Theme.of(context)
                        .textTheme
                        .titleSmall
                        ?.copyWith(fontWeight: FontWeight.w700),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    formatter.format(result.createdAt),
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: AppColors.textSecondary),
                  ),
                  const SizedBox(height: 8),
                  VerdictBadge(verdict: result.verdict, compact: true),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: AppColors.textSecondary),
          ],
        ),
      ),
    );
  }
}
