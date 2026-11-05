import 'package:flutter/material.dart';

import 'media_item.dart';

enum Verdict { authentic, suspected, inconclusive }

class PriorAnalysis {
  PriorAnalysis({
    required this.id,
    required this.prediction,
    required this.confidence,
    required this.band,
    required this.createdAt,
    this.heatmapUrl,
  });

  final String id;
  final String prediction;
  final double confidence;
  final String band;
  final DateTime createdAt;
  final String? heatmapUrl;

  factory PriorAnalysis.fromJson(Map<String, dynamic> json) {
    return PriorAnalysis(
      id: json['id']?.toString() ?? '',
      prediction: json['prediction'] as String? ?? 'Unknown',
      confidence: _normalizeConfidence(json['confidence']),
      band: json['band'] as String? ?? 'Unknown',
      createdAt: _parseDate(json['created_at']),
      heatmapUrl: json['heatmap_url'] as String?,
    );
  }
}

class AnalysisResult {
  AnalysisResult({
    required this.id,
    required this.prediction,
    required this.confidence,
    required this.band,
    required this.type,
    required this.createdAt,
    required this.mediaItem,
    required this.processingTimeSeconds,
    required this.filename,
    required this.isDuplicate,
    required this.priorAnalyses,
    this.heatmapUrl,
    this.thresholds,
    this.details,
    this.reportUrl,
    this.blockchainStatus,
    this.polygonUrl,
    this.blockchainTxHash,
    this.blockNumber,
    // Keep old fields to prevent compilation errors temporarily
    this.mediaTitle = '',
    this.mediaUrl = '',
    this.blockchainHash = '',
    this.explanation = '',
  });

  final String id;
  final String prediction;
  final double confidence;
  final String band;
  final String type;
  final String? heatmapUrl;
  final Map<String, dynamic>? thresholds;
  final Map<String, dynamic>? details;
  final String? reportUrl;
  final String? blockchainStatus;
  final String? polygonUrl;
  final String? blockchainTxHash;
  final int? blockNumber;
  final double processingTimeSeconds;
  final String filename;
  final bool isDuplicate;
  final List<PriorAnalysis> priorAnalyses;
  final DateTime createdAt;
  final MediaItem mediaItem;

  // Legacy fields (optional / defaults)
  final String mediaTitle;
  final String mediaUrl;
  final String blockchainHash;
  final String explanation;

  Verdict get verdict {
    final lower = prediction.toLowerCase();
    if (lower.contains('manipulated') || lower.contains('ai-generated')) {
      return Verdict.suspected;
    }
    if (lower.contains('authentic')) {
      return Verdict.authentic;
    }
    return Verdict.inconclusive;
  }

  String get verdictLabel => prediction;

  double get displayConfidence {
    final lower = prediction.toLowerCase();
    if (lower.contains('ai-generated')) {
      return aiProbability ?? confidence;
    }
    if (lower.contains('authentic')) {
      return (1 - confidence).clamp(0.0, 1.0).toDouble();
    }
    return confidence;
  }

  double? get aiProbability {
    final value = details?['ai_prob'];
    if (value is! num) return null;
    return _normalizeConfidence(value);
  }

  double? get manipulationProbability {
    final value = details?['ucf_prob'];
    if (value is num) return _normalizeConfidence(value);
    return confidence;
  }

  Color get verdictColor {
    switch (verdict) {
      case Verdict.authentic:
        return Colors.greenAccent;
      case Verdict.suspected:
        return Colors.redAccent;
      case Verdict.inconclusive:
        return Colors.amberAccent;
    }
  }

  factory AnalysisResult.fromJson(Map<String, dynamic> json, MediaItem media) {
    var analysesList = <PriorAnalysis>[];
    final rawPriorAnalyses = json['prior_analyses'];
    if (rawPriorAnalyses is List) {
      analysesList = rawPriorAnalyses
          .whereType<Map<String, dynamic>>()
          .map(PriorAnalysis.fromJson)
          .toList();
    }

    return AnalysisResult(
      id: json['analysis_id']?.toString() ?? json['id']?.toString() ?? '',
      prediction: json['prediction'] as String? ?? 'Unknown',
      confidence: _normalizeConfidence(json['confidence']),
      band: json['band'] as String? ?? 'Unknown',
      type:
          json['type'] as String? ??
          json['media_type'] as String? ??
          media.type,
      heatmapUrl: json['heatmap_url'] as String?,
      thresholds: json['thresholds'] is Map<String, dynamic>
          ? json['thresholds'] as Map<String, dynamic>
          : null,
      details: json['details'] is Map<String, dynamic>
          ? json['details'] as Map<String, dynamic>
          : null,
      reportUrl: json['report_url'] as String? ?? json['pdf_url'] as String?,
      blockchainStatus: json['blockchain_status'] as String?,
      polygonUrl: json['polygon_url'] as String?,
      blockchainTxHash: json['blockchain_tx_hash'] as String?,
      blockNumber: (json['block_number'] as num?)?.toInt(),
      processingTimeSeconds:
          (json['processing_time_seconds'] as num?)?.toDouble() ?? 0.0,
      filename: json['filename'] as String? ?? media.title,
      isDuplicate: json['is_duplicate'] as bool? ?? false,
      priorAnalyses: analysesList,
      createdAt: _parseDate(json['created_at']),
      mediaItem: media,
      mediaTitle: media.title,
      mediaUrl: media.url,
      blockchainHash: json['blockchain_tx_hash'] as String? ?? _fakeHash(),
      explanation:
          'Analysis processed in ${(json['processing_time_seconds'] as num?)?.toDouble() ?? 0.0} seconds.',
    );
  }

  static String _fakeHash() {
    const chars = 'abcdef0123456789';
    final rand = DateTime.now().microsecondsSinceEpoch;
    return List.generate(
      64,
      (index) => chars[(rand + index) % chars.length],
    ).join();
  }

  AnalysisResult copyWith({
    String? reportUrl,
    String? blockchainStatus,
    String? polygonUrl,
    String? blockchainTxHash,
    int? blockNumber,
  }) {
    return AnalysisResult(
      id: id,
      prediction: prediction,
      confidence: confidence,
      band: band,
      type: type,
      createdAt: createdAt,
      mediaItem: mediaItem,
      processingTimeSeconds: processingTimeSeconds,
      filename: filename,
      isDuplicate: isDuplicate,
      priorAnalyses: priorAnalyses,
      heatmapUrl: heatmapUrl,
      thresholds: thresholds,
      details: details,
      reportUrl: reportUrl ?? this.reportUrl,
      blockchainStatus: blockchainStatus ?? this.blockchainStatus,
      polygonUrl: polygonUrl ?? this.polygonUrl,
      blockchainTxHash: blockchainTxHash ?? this.blockchainTxHash,
      blockNumber: blockNumber ?? this.blockNumber,
      mediaTitle: mediaTitle,
      mediaUrl: mediaUrl,
      blockchainHash:
          blockchainTxHash ?? this.blockchainTxHash ?? blockchainHash,
      explanation: explanation,
    );
  }
}

double _normalizeConfidence(dynamic value) {
  final parsed = (value as num?)?.toDouble() ?? 0.0;
  if (parsed.isNaN || parsed.isInfinite) {
    return 0.0;
  }
  final normalized = parsed > 1 ? parsed / 100 : parsed;
  return normalized.clamp(0.0, 1.0).toDouble();
}

DateTime _parseDate(dynamic value) {
  if (value is! String || value.trim().isEmpty) {
    return DateTime.now();
  }
  return DateTime.tryParse(value)?.toLocal() ?? DateTime.now();
}
