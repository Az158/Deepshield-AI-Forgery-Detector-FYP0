import 'dart:math';

import '../models/analysis_result.dart';
import '../models/media_item.dart';
import 'history_service.dart';

/// Fake analyzer that simulates latency and returns dummy results.
class FakeAnalysisService {
  FakeAnalysisService({required this.historyService});

  final HistoryService historyService;
  final _random = Random();

  Future<AnalysisResult> analyzeMedia(MediaItem media) async {
    await Future.delayed(const Duration(seconds: 2));

    final verdicts = Verdict.values;
    final verdict = verdicts[_random.nextInt(verdicts.length)];
    final confidence = 60 + _random.nextInt(35) + _random.nextDouble();

    final result = AnalysisResult(
      id: DateTime.now().microsecondsSinceEpoch.toString(),
      prediction: verdict.name,
      confidence: confidence.clamp(0, 100),
      band: 'all',
      type: 'video',
      createdAt: DateTime.now(),
      mediaItem: media,
      processingTimeSeconds: 2.0,
      filename: media.title,
      isDuplicate: false,
      priorAnalyses: [],
      reportUrl: null,
      blockchainStatus: 'pending',
      polygonUrl: null,
      blockchainTxHash: null,
      blockchainHash: _fakeHash(),
      explanation:
          'Our model detected subtle frame inconsistencies suggesting possible manipulation. This is simulated data for MVP.',
      mediaTitle: media.title,
      mediaUrl: media.url,
    );

    historyService.addResult(result);
    return result;
  }

  String _fakeHash() {
    const chars = 'abcdef0123456789';
    return List.generate(
      64,
      (_) => chars[_random.nextInt(chars.length)],
    ).join();
  }
}
