import '../models/analysis_result.dart';

/// In-memory history store for simulated analysis results.
class HistoryService {
  final List<AnalysisResult> _history = [];

  List<AnalysisResult> getHistory() {
    final list = List<AnalysisResult>.from(_history);
    list.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return list;
  }

  void addResult(AnalysisResult result) {
    _history.removeWhere((item) => item.id == result.id);
    _history.add(result);
  }
}
