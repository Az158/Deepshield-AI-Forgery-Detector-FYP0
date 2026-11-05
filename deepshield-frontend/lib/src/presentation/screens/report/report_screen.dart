import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:intl/intl.dart';

import '../../../core/constants.dart';
import '../../../core/theme.dart';
import '../../../core/utils/report_downloader.dart';
import '../../../core/utils/service_locator.dart';
import '../../../data/models/report_summary.dart';
import '../../widgets/primary_button.dart';
import '../../widgets/verdict_badge.dart';

/// Report detail UI built from simulated data.
class ReportScreen extends StatelessWidget {
  const ReportScreen({super.key, required this.summary});

  final ReportSummary summary;

  Future<void> _downloadReport(BuildContext context) async {
    final reportUrl = summary.result.reportUrl;
    if (reportUrl == null || reportUrl.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Report is not ready yet.')),
      );
      return;
    }

    final token = ServiceLocator.authProvider.token;
    if (token == null || token.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please log in to download reports.')),
      );
      return;
    }

    try {
      await downloadAndOpenReport(
        context: context,
        reportUrl: reportUrl,
        token: token,
      );
    } catch (_) {
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Could not download the report. Check your connection and retry.',
          ),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final result = summary.result;
    final confidencePercent = result.displayConfidence * 100;
    final reportReady = result.reportUrl != null && result.reportUrl!.isNotEmpty;
    return Scaffold(
      appBar: AppBar(title: const Text('Report')),
      body: SingleChildScrollView(
        padding: AppSpacing.screenPadding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                VerdictBadge(verdict: result.verdict),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Text(
                    '${confidencePercent.toStringAsFixed(1)}% confidence',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            _section(
              context,
              title: 'Result summary',
              child: Text(
                'This report summarizes the AI classification, confidence, available visual evidence, and verification status.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            _section(
              context,
              title: 'Media metadata',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _row('Title', result.mediaTitle),
                  _row('URL', result.mediaUrl),
                  _row('Type', summary.mediaType),
                  _row('Duration', summary.duration),
                  _row('Size', summary.size),
                  _row(
                    'Analyzed on',
                    DateFormat('MMM d, y, h:mm a').format(result.createdAt),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            _section(
              context,
              title: 'Visual explanation',
              child: ClipRRect(
                borderRadius: AppRadii.card,
                child: _buildHeatmapPreview(
                  result.heatmapUrl,
                  summary.heatmapAsset,
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            _section(
              context,
              title: 'Blockchain',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _row('Status', result.blockchainStatus ?? 'Pending'),
                  _row('Hash', result.blockchainTxHash ?? result.blockchainHash),
                  _row(
                    'Timestamp',
                    DateFormat('MMM d, h:mm a').format(result.createdAt),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Center(
                    child: Container(
                      padding: const EdgeInsets.all(AppSpacing.md),
                      decoration: BoxDecoration(
                        color: AppColors.surface,
                        borderRadius: AppRadii.card,
                        border: Border.all(color: AppColors.border),
                      ),
                      child: _buildQrPreview(summary.qrPlaceholderAsset),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            if (!reportReady) ...[
              Text(
                'The PDF is not ready yet. Return to the result screen and retry the report status check.',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: AppSpacing.sm),
            ],
            PrimaryButton(
              label: 'Download report',
              icon: const Icon(Icons.download_rounded, color: Colors.white),
              onPressed: reportReady ? () => _downloadReport(context) : null,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeatmapPreview(String? heatmapUrl, String? fallbackAsset) {
    if (heatmapUrl != null && heatmapUrl.isNotEmpty) {
      return Image.network(
        heatmapUrl,
        height: 180,
        width: double.infinity,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) {
          return Container(
            height: 180,
            width: double.infinity,
            color: Colors.grey[800],
            child: const Center(child: Text('Heatmap unavailable')),
          );
        },
      );
    }

    if (fallbackAsset != null && fallbackAsset.isNotEmpty) {
      return SvgPicture.asset(
        fallbackAsset,
        height: 180,
        width: double.infinity,
        fit: BoxFit.cover,
      );
    }

    return Container(
      height: 180,
      width: double.infinity,
      color: Colors.grey[800],
      child: const Center(child: Text('Heatmap unavailable')),
    );
  }

  Widget _buildQrPreview(String? assetPath) {
    if (assetPath != null && assetPath.isNotEmpty) {
      return SvgPicture.asset(
        assetPath,
        height: 140,
        width: 140,
        fit: BoxFit.cover,
      );
    }

    return const SizedBox(
      height: 140,
      width: 140,
      child: Icon(Icons.image_not_supported, color: Colors.grey),
    );
  }

  Widget _section(
    BuildContext context, {
    required String title,
    required Widget child,
  }) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.cardOverlay,
        borderRadius: AppRadii.card,
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: AppSpacing.sm),
          child,
        ],
      ),
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: AppColors.textSecondary),
            ),
          ),
          Expanded(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: const TextStyle(fontWeight: FontWeight.w600),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}
