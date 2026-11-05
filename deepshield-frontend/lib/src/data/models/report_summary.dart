import 'analysis_result.dart';

/// Simplified report summary used on the report detail screen.
class ReportSummary {
  ReportSummary({
    required this.result,
    required this.mediaType,
    required this.duration,
    required this.size,
    required this.qrPlaceholderAsset,
    required this.heatmapAsset,
  });

  final AnalysisResult result;
  final String mediaType;
  final String duration;
  final String size;
  final String qrPlaceholderAsset;
  final String heatmapAsset;
}
