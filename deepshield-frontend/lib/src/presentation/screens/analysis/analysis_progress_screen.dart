import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';

import '../../../core/constants.dart';
import '../../../core/environment.dart';
import '../../../core/theme.dart';
import '../../../core/utils/authenticated_http.dart';
import '../../../core/utils/service_locator.dart';
import '../../../data/models/analysis_result.dart';
import '../../../routes/app_router.dart';
import '../../../data/models/deepfake_request.dart';
import '../../../data/services/deepfake_service.dart';

/// Animated analysis status screen that calls the deepfake backend.
class AnalysisProgressScreen extends StatefulWidget {
  const AnalysisProgressScreen({super.key, required this.request});

  final DeepfakeRequest request;

  @override
  State<AnalysisProgressScreen> createState() => _AnalysisProgressScreenState();
}

class _AnalysisProgressScreenState extends State<AnalysisProgressScreen> {
  bool uploadingDone = false;
  bool aiDone = false;
  bool reportDone = false;
  bool chainDone = false;
  bool hasError = false;
  String? _activeStage = 'Upload';
  String? _failedStage;
  String? errorMessage;
  static const int _maxStatusPolls = 36;

  @override
  void initState() {
    super.initState();
    _runAnalysis();
  }

  Future<void> _runAnalysis() async {
    setState(() {
      uploadingDone = false;
      aiDone = false;
      reportDone = false;
      chainDone = false;
      hasError = false;
      _activeStage = 'Upload';
      _failedStage = null;
      errorMessage = null;
    });

    try {
      await Future.delayed(const Duration(milliseconds: 300));
      if (!mounted) return;
      setState(() {
        uploadingDone = true;
        _activeStage = 'AI Check';
      });

      final result = await ServiceLocator.deepfakeService.analyze(
        widget.request,
      );
      if (!mounted) return;
      setState(() {
        aiDone = true;
        _activeStage = 'Blockchain';
      });

      final finalResult = await _waitForCompletion(result);
      if (!mounted) return;

      Navigator.pushReplacementNamed(
        context,
        AppRoutes.result,
        arguments: finalResult,
      );
    } on UnauthorizedException {
      if (!mounted) return;
      await handleUnauthorized(context);
    } catch (e) {
      if (!mounted) return;

      final rawError = e.toString();
      final displayError = rawError.startsWith('Exception: ')
          ? rawError.substring('Exception: '.length)
          : rawError;
      final failedStage = _stageForError(displayError);

      setState(() {
        hasError = true;
        _failedStage = failedStage;
        _activeStage = null;
        errorMessage = _actionableError(displayError, failedStage);
      });
    }
  }

  String _stageForError(String message) {
    final lower = message.toLowerCase();
    if (lower.contains('blockchain') ||
        lower.contains('anchor') ||
        lower.contains('chain')) {
      return 'Blockchain';
    }
    if (lower.contains('report') ||
        lower.contains('pdf') ||
        lower.contains('finalizing')) {
      return 'Report';
    }
    if (lower.contains('file') ||
        lower.contains('upload') ||
        lower.contains('format') ||
        lower.contains('50mb')) {
      return 'Upload';
    }
    return 'AI Check';
  }

  String _actionableError(String message, String stage) {
    if (stage == 'Upload') {
      return '$message Choose a supported file, then retry the upload.';
    }
    if (stage == 'Blockchain') {
      return '$message Retry the analysis; it stopped during blockchain anchoring. If it fails again, check the backend blockchain logs.';
    }
    if (stage == 'Report') {
      return '$message Retry the analysis; it stopped during report generation. If it fails again, check the backend report logs.';
    }
    if (message.toLowerCase().contains('timed out')) {
      return '$message Retry the analysis, or try a smaller file if it happens again.';
    }
    return '$message Retry the analysis. If it fails again, re-upload the file.';
  }

  Future<AnalysisResult> _waitForCompletion(AnalysisResult initial) async {
    if (_isComplete(initial)) {
      setState(() {
        chainDone = _isBlockchainResolved(initial.blockchainStatus);
        reportDone = initial.reportUrl != null && initial.reportUrl!.isNotEmpty;
        _activeStage = null;
      });
      return initial;
    }

    final token = ServiceLocator.authProvider.token;
    if (token == null || token.isEmpty) {
      throw Exception(
        'Your session expired before finalizing the report. Log in again, then re-run the analysis.',
      );
    }

    if (initial.id.isEmpty) {
      throw Exception(
        'The backend did not return an analysis ID. Re-run the analysis so report and blockchain status can be tracked.',
      );
    }

    var latest = initial;
    for (var attempt = 0; attempt < _maxStatusPolls; attempt++) {
      await Future.delayed(const Duration(seconds: 5));
      if (!mounted) return latest;

      final next = await _fetchLatestResult(latest, token);
      latest = next;

      final blockchainResolved = _isBlockchainResolved(next.blockchainStatus);
      final reportReady = next.reportUrl != null && next.reportUrl!.isNotEmpty;

      if (!mounted) return latest;
      setState(() {
        chainDone = blockchainResolved;
        reportDone = reportReady;
        _activeStage = blockchainResolved ? 'Report' : 'Blockchain';
      });

      if (blockchainResolved && reportReady) {
        if (!mounted) return next;
        setState(() => _activeStage = null);
        return next;
      }
    }

    final failedStage = chainDone ? 'Report' : 'Blockchain';
    throw Exception(
      failedStage == 'Report'
          ? 'Report generation did not finish in time. Retry the analysis, or check backend post-analysis logs.'
          : 'Blockchain anchoring did not finish in time. Retry the analysis, or check backend blockchain logs.',
    );
  }

  Future<AnalysisResult> _fetchLatestResult(
    AnalysisResult current,
    String token,
  ) async {
    final baseUrl = _resolveBaseUrl(
      Environment.aiServiceUrl,
    ).replaceAll(RegExp(r'/+$'), '');
    final response = await authenticatedGet(
      '$baseUrl/analyses/${current.id}',
      token,
      context,
      timeout: const Duration(seconds: 10),
    );

    if (response.statusCode != 200) {
      throw Exception(
        'Could not refresh analysis status. Retry the analysis, or check the backend.',
      );
    }

    final decoded = jsonDecode(response.body);
    if (decoded is! Map<String, dynamic>) {
      throw Exception(
        'Backend returned an unexpected status response. Check the analysis status endpoint.',
      );
    }

    final reportUrl =
        decoded['report_url']?.toString() ?? decoded['pdf_url']?.toString();
    final blockchainStatus =
        decoded['blockchain_status']?.toString() ??
        decoded['status']?.toString();
    final blockchainTxHash =
        decoded['blockchain_tx_hash']?.toString() ??
        decoded['tx_hash']?.toString();
    final polygonUrl =
        decoded['polygon_url']?.toString() ??
        decoded['verification_url']?.toString();
    final rawBlockNumber = decoded['block_number'];
    final blockNumber = rawBlockNumber is num
        ? rawBlockNumber.toInt()
        : int.tryParse(rawBlockNumber?.toString() ?? '');

    return current.copyWith(
      reportUrl: reportUrl,
      blockchainStatus: blockchainStatus,
      blockchainTxHash: blockchainTxHash,
      polygonUrl: polygonUrl,
      blockNumber: blockNumber,
    );
  }

  bool _isComplete(AnalysisResult result) {
    return _isBlockchainResolved(result.blockchainStatus) &&
        result.reportUrl != null &&
        result.reportUrl!.isNotEmpty;
  }

  bool _isBlockchainResolved(String? status) {
    final normalized = status?.toLowerCase() ?? '';
    return normalized == 'confirmed' ||
        normalized == 'failed' ||
        normalized == 'anchored';
  }

  String _resolveBaseUrl(String url) {
    try {
      final uri = Uri.parse(url);
      final isLocalHost = uri.host == 'localhost' || uri.host == '127.0.0.1';
      if (isLocalHost && Platform.isAndroid) {
        return uri.replace(host: '10.0.2.2').toString();
      }
      return url;
    } catch (_) {
      return url;
    }
  }

  @override
  Widget build(BuildContext context) {
    final isVideo = widget.request.mediaType.toLowerCase() == 'video';

    return Scaffold(
      appBar: AppBar(title: const Text('Content Analysis')),
      body: Padding(
        padding: AppSpacing.screenPadding,
        child: Column(
          children: [
            const SizedBox(height: AppSpacing.md),
            TweenAnimationBuilder<double>(
              tween: Tween(begin: 0.92, end: 1.0),
              duration: const Duration(milliseconds: 800),
              curve: Curves.easeOutBack,
              builder: (context, value, _) {
                return Transform.scale(
                  scale: value,
                  child: Container(
                    height: 120,
                    width: 120,
                    decoration: const BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: SweepGradient(
                        colors: [
                          AppColors.primary,
                          AppColors.secondary,
                          AppColors.primary,
                        ],
                      ),
                    ),
                    child: const Center(
                      child: CircleAvatar(
                        radius: 52,
                        backgroundColor: AppColors.surface,
                        child: Icon(
                          Icons.shield_rounded,
                          size: 40,
                          color: AppColors.primary,
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
            const SizedBox(height: AppSpacing.lg),
            Text(
              'Analyzing Content',
              style: Theme.of(
                context,
              ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              'Upload -> AI Check -> Blockchain -> Report',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.lg),
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: LinearProgressIndicator(
                value: reportDone
                    ? 1
                    : chainDone
                    ? 0.75
                    : aiDone
                    ? 0.55
                    : uploadingDone
                    ? 0.35
                    : 0.1,
                backgroundColor: AppColors.border,
                color: AppColors.primary,
                minHeight: 8,
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            Expanded(
              child: ListView(
                children: [
                  _stepTile(
                    icon: Icons.upload_rounded,
                    label: 'Upload',
                    description: 'Preparing your selected file for analysis.',
                    done: uploadingDone,
                    inProgress: _activeStage == 'Upload',
                    failed: _failedStage == 'Upload',
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  _stepTile(
                    icon: Icons.psychology_alt_outlined,
                    label: 'AI Check',
                    description: isVideo
                        ? 'Checking video frames for signs of manipulation.'
                        : 'Checking image evidence for signs of manipulation.',
                    done: aiDone,
                    inProgress: _activeStage == 'AI Check',
                    failed: _failedStage == 'AI Check',
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  _stepTile(
                    icon: Icons.shield_outlined,
                    label: 'Blockchain',
                    description:
                        'Anchoring the report hash before showing the result.',
                    done: chainDone,
                    inProgress: _activeStage == 'Blockchain',
                    failed: _failedStage == 'Blockchain',
                    queued:
                        !chainDone &&
                        _activeStage != 'Blockchain' &&
                        _activeStage != null,
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  _stepTile(
                    icon: Icons.description_outlined,
                    label: 'Report',
                    description:
                        'Generating the downloadable forensic PDF.',
                    done: reportDone,
                    inProgress: _activeStage == 'Report',
                    failed: _failedStage == 'Report',
                    queued:
                        !reportDone &&
                        _activeStage != 'Report' &&
                        _activeStage != null,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  Text(
                    'The result opens after blockchain anchoring and report generation finish.',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  if (hasError) ...[
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      errorMessage ??
                          'Analysis stopped before completion. Retry the analysis, or re-upload the file.',
                      style: Theme.of(
                        context,
                      ).textTheme.bodyMedium?.copyWith(color: Colors.redAccent),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton.icon(
                            onPressed: _runAnalysis,
                            icon: const Icon(Icons.refresh_rounded),
                            label: Text(
                              _failedStage == 'Upload'
                                  ? 'Retry upload'
                                  : 'Retry analysis',
                            ),
                          ),
                        ),
                        const SizedBox(width: AppSpacing.sm),
                        Expanded(
                          child: OutlinedButton(
                            onPressed: () => Navigator.pop(context),
                            child: const Text('Go back'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _stepTile({
    required IconData icon,
    required String label,
    required String description,
    required bool done,
    bool inProgress = false,
    bool failed = false,
    bool queued = false,
  }) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: AppRadii.card,
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          CircleAvatar(
            backgroundColor: failed
                ? Colors.redAccent
                : done
                ? Colors.green
                : queued
                ? AppColors.border
                : AppColors.primary,
            child: Icon(icon, color: Colors.white),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 2),
                Text(
                  failed
                      ? 'Failed here. Use the retry action below.'
                      : description,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          if (done)
            const Icon(Icons.check_circle, color: Colors.greenAccent)
          else if (failed)
            const Icon(Icons.error_outline, color: Colors.redAccent)
          else if (queued)
            const Icon(Icons.schedule_rounded, color: AppColors.textSecondary)
          else if (inProgress && !hasError)
            const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
        ],
      ),
    );
  }
}
