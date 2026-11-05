import 'dart:async';

import 'package:flutter/material.dart';

import '../services/analysis_service.dart';

class AnalysisStatusProvider extends ChangeNotifier {
  AnalysisStatusProvider({required AnalysisService analysisService})
    : _analysisService = analysisService;

  final AnalysisService _analysisService;

  Timer? _timer;
  int _attempts = 0;
  bool _isFetching = false;

  String? _reportUrl;
  String _blockchainStatus = 'unknown';
  String? _polygonUrl;
  String? _txHash;
  bool _isPolling = false;

  String? get reportUrl => _reportUrl;
  String get blockchainStatus => _blockchainStatus;
  String? get polygonUrl => _polygonUrl;
  String? get txHash => _txHash;
  bool get isPolling => _isPolling;
  bool get reportReady => _reportUrl != null;
  bool get blockchainResolved =>
      _blockchainStatus == 'confirmed' || _blockchainStatus == 'failed';

  void initialise({
    required String? reportUrl,
    required String? blockchainStatus,
    required String? polygonUrl,
    required String? txHash,
  }) {
    stopPolling();
    _reportUrl = reportUrl;
    _blockchainStatus = blockchainStatus ?? 'unknown';
    _polygonUrl = polygonUrl;
    _txHash = txHash;
    _attempts = 0;
    _isFetching = false;
    _isPolling = false;
    notifyListeners();
  }

  void startPolling(String analysisId, String token) {
    // debug: ensure analysisId is passed correctly
    // ignore: avoid_print
    print('AnalysisStatusProvider.startPolling -> analysisId: "$analysisId"');
    if (reportReady && blockchainResolved) {
      return;
    }

    stopPolling();
    _isPolling = true;
    _attempts = 0;
    notifyListeners();

    _timer = Timer.periodic(const Duration(seconds: 5), (timer) async {
      if (_isFetching) {
        return;
      }
      if (_attempts >= 10) {
        stopPolling();
        return;
      }
      _attempts += 1;
      _isFetching = true;

      final result = await _analysisService.fetchAnalysisStatus(
        analysisId,
        token,
      );

      _isFetching = false;

      if (!result.success) {
        if (result.errorMessage == 'not_found' ||
            result.errorMessage == 'network_error') {
          if (_attempts >= 10) {
            stopPolling();
          }
          return;
        }
        return;
      }

      _reportUrl = result.reportUrl ?? _reportUrl;
      _blockchainStatus = result.blockchainStatus ?? _blockchainStatus;
      _polygonUrl = result.polygonUrl ?? _polygonUrl;
      _txHash = result.blockchainTxHash ?? _txHash;
      notifyListeners();

      if (reportReady && blockchainResolved) {
        stopPolling();
        return;
      }

      if (_attempts >= 10) {
        stopPolling();
      }
    });
  }

  void stopPolling() {
    _timer?.cancel();
    _timer = null;
    _isFetching = false;
    _isPolling = false;
    notifyListeners();
  }
}
