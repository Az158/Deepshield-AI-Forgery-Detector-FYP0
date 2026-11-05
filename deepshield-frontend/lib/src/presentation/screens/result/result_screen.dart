import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import '../../../core/constants.dart';
import '../../../core/environment.dart';
import '../../../core/theme.dart';
import '../../../core/utils/authenticated_http.dart';
import '../../../core/utils/report_downloader.dart';
import '../../../core/utils/service_locator.dart';
import '../../../data/models/analysis_result.dart';
import '../../../data/models/report_summary.dart';
import '../../../routes/app_router.dart';
import '../../widgets/primary_button.dart';

class ResultScreen extends StatefulWidget {
  const ResultScreen({super.key, required this.result});

  final AnalysisResult result;

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  final Set<String> _expandedHistoryItems = {};

  Timer? _pollingTimer;
  int _pollCount = 0;
  static const int _maxPolls = 12;

  String? _reportUrl;
  String _blockchainStatus = 'pending';
  String _analysisId = '';
  String? _blockchainTxHash;
  String? _polygonUrl;
  int? _blockNumber;
  bool _reportReady = false;
  bool _blockchainResolved = false;
  bool _isDownloading = false;
  bool _showHeatmap = true;

  void _log(String message) {
    debugPrint('[ResultScreen] $message');
  }

  @override
  void initState() {
    super.initState();

    final result = widget.result;
    _reportUrl = result.reportUrl;
    _analysisId = result.id;
    _blockchainStatus = result.blockchainStatus ?? 'pending';
    _blockchainTxHash = result.blockchainTxHash;
    _polygonUrl = result.polygonUrl;
    _blockNumber = result.blockNumber;
    _reportReady = _reportUrl != null && _reportUrl!.isNotEmpty;
    _blockchainResolved =
        _blockchainStatus == 'confirmed' || _blockchainStatus == 'failed';

    _log(
      'initState analysisId=${widget.result.id} reportUrl=$_reportUrl '
      'reportReady=$_reportReady blockchainStatus=$_blockchainStatus '
      'blockchainResolved=$_blockchainResolved',
    );

    if (_analysisId.isEmpty) {
      _log('analysis id missing, attempting to resolve via history');
      _tryResolveAnalysisId();
    }

    if (!_reportReady || !_blockchainResolved) {
      _startPolling();
    } else {
      _log(
        'polling not started because both report and blockchain are resolved',
      );
    }
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }

  void _startPolling() {
    _pollingTimer?.cancel();
    _log('starting polling for analysisId=$_analysisId');
    _pollingTimer = Timer.periodic(const Duration(seconds: 5), (timer) async {
      if (_pollCount >= _maxPolls) {
        _log('polling stopped due to max polls reached ($_maxPolls)');
        timer.cancel();
        return;
      }

      _pollCount++;
      _log(
        'poll tick=$_pollCount/$_maxPolls reportReady=$_reportReady blockchainResolved=$_blockchainResolved',
      );
      await _pollAnalysisStatus();

      if (_reportReady && _blockchainResolved) {
        _log('polling resolved, stopping timer');
        timer.cancel();
      }
    });
  }

  Future<void> _pollAnalysisStatus() async {
    try {
      final authProvider = ServiceLocator.authProvider;
      final token = authProvider.token;
      final analysisId = _analysisId;

      if (token == null || token.isEmpty || analysisId.isEmpty) {
        _log(
          'poll skipped tokenEmpty=${token == null || token.isEmpty} analysisIdEmpty=${analysisId.isEmpty}',
        );
        return;
      }

      final baseUrl = _resolveBaseUrl(
        Environment.aiServiceUrl,
      ).replaceAll(RegExp(r'/+$'), '');
      final url = '$baseUrl/analyses/$analysisId';
      _log('poll request url=$url tokenPresent=${token.isNotEmpty}');

      final response = await authenticatedGet(
        url,
        token,
        context,
        timeout: const Duration(seconds: 8),
      );

      _log(
        'poll response status=${response.statusCode} body=${_clip(response.body)}',
      );

      if (!mounted) {
        return;
      }

      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body);
        if (decoded is! Map<String, dynamic>) {
          _log('poll ignored unexpected response shape');
          return;
        }
        final data = decoded;
        final nextReportUrl =
            data['pdf_url'] as String? ?? data['report_url'] as String?;
        final nextBlockchainStatus =
            data['blockchain_status'] as String? ?? 'pending';
        final nextBlockchainTxHash = data['blockchain_tx_hash'] as String?;
        final nextPolygonUrl = data['polygon_url'] as String?;
        final nextBlockNumber = (data['block_number'] as num?)?.toInt();
        final nextReportReady =
            nextReportUrl != null && nextReportUrl.isNotEmpty;
        final nextBlockchainResolved =
            nextBlockchainStatus == 'confirmed' ||
            nextBlockchainStatus == 'failed';

        _log(
          'parsed poll data pdf_url=$nextReportUrl '
          'blockchain_status=$nextBlockchainStatus '
          'txHashPresent=${nextBlockchainTxHash != null && nextBlockchainTxHash.isNotEmpty} '
          'polygonPresent=${nextPolygonUrl != null && nextPolygonUrl.isNotEmpty} '
          'reportReady=$nextReportReady blockchainResolved=$nextBlockchainResolved',
        );

        setState(() {
          _reportUrl = nextReportUrl;
          _blockchainStatus = nextBlockchainStatus;
          _blockchainTxHash = nextBlockchainTxHash;
          _polygonUrl = nextPolygonUrl;
          _blockNumber = nextBlockNumber;
          _reportReady = nextReportReady;
          _blockchainResolved = nextBlockchainResolved;
        });
      } else {
        _log('poll non-200 response status=${response.statusCode}');
      }
    } catch (e, st) {
      _log('poll exception=$e');
      _log('poll stack=${_clip(st.toString(), max: 800)}');
      // Polling errors are intentionally ignored to keep UI stable.
    }
  }

  Future<void> _tryResolveAnalysisId() async {
    try {
      final authProvider = ServiceLocator.authProvider;
      final token = authProvider.token;
      if (token == null || token.isEmpty) return;

      final baseUrl = _resolveBaseUrl(
        Environment.aiServiceUrl,
      ).replaceAll(RegExp(r'/+$'), '');
      final url = '$baseUrl/analyses/history';
      _log('resolve id: fetching history $url');
      final resp = await authenticatedGet(url, token, context);
      if (resp.statusCode != 200) return;
      final decoded = jsonDecode(resp.body);
      final raw = decoded is Map<String, dynamic>
          ? (decoded['analyses'] ?? decoded['items'] ?? decoded['data'])
          : decoded;
      final List<dynamic> analysesRaw = raw is List ? raw : <dynamic>[];

      final targetFilename = widget.result.filename;
      for (final item in analysesRaw.whereType<Map<String, dynamic>>()) {
        final fname = item['filename']?.toString() ?? '';
        if (fname == targetFilename) {
          final foundId = item['id']?.toString() ?? '';
          if (foundId.isNotEmpty) {
            setState(() {
              _analysisId = foundId;
            });
            _log('resolved analysis id=$_analysisId by filename match');
            return;
          }
        }
      }
    } catch (e) {
      _log('resolve id failed: $e');
    }
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

  Future<void> _downloadPdf() async {
    if (_reportUrl == null) {
      _log('download blocked: reportUrl is null');
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Report is not ready yet. Wait a moment, then retry.'),
        ),
      );
      return;
    }

    if (_reportUrl!.isEmpty) {
      _log('download blocked: reportUrl is empty');
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Report link is missing. Retry report status refresh.'),
        ),
      );
      return;
    }

    setState(() {
      _isDownloading = true;
    });

    try {
      final authProvider = ServiceLocator.authProvider;
      final token = authProvider.token;
      if (token == null || token.isEmpty) {
        _log('download blocked: auth token missing');
        throw Exception('Not authenticated');
      }

      _log('download request url=$_reportUrl tokenPresent=${token.isNotEmpty}');

      await downloadAndOpenReport(
        context: context,
        reportUrl: _reportUrl!,
        token: token,
      );
    } catch (e, st) {
      _log('download exception=$e');
      _log('download stack=${_clip(st.toString(), max: 800)}');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Could not download the report. Check your connection and retry.',
            ),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isDownloading = false;
        });
      }
    }
  }

  String _clip(String value, {int max = 400}) {
    if (value.length <= max) {
      return value;
    }
    return '${value.substring(0, max)}...';
  }

  Widget _buildDownloadButton() {
    return ElevatedButton.icon(
      icon: _isDownloading
          ? const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: Colors.white,
              ),
            )
          : const Icon(Icons.download),
      label: Text(_isDownloading ? 'Downloading...' : 'Download PDF'),
      onPressed: _isDownloading ? null : _downloadPdf,
    );
  }

  AnalysisResult _currentResult() {
    return widget.result.copyWith(
      reportUrl: _reportUrl,
      blockchainStatus: _blockchainStatus,
      polygonUrl: _polygonUrl,
      blockchainTxHash: _blockchainTxHash,
    );
  }

  Widget _buildCard({required String title, required Widget child}) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.cardOverlay,
        borderRadius: AppRadii.card,
        boxShadow: const [AppShadows.soft],
        border: Border.all(color: AppColors.subtle),
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

  Widget _buildForensicReportCard() {
    if (_reportReady && _reportUrl != null) {
      return _buildCard(
        title: 'Forensic Report',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.check_circle, color: Colors.green),
                SizedBox(width: 8),
                Text('Report ready'),
              ],
            ),
            const SizedBox(height: 12),
            _buildDownloadButton(),
          ],
        ),
      );
    } else if (_pollCount >= _maxPolls) {
      return _buildCard(
        title: 'Forensic Report',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'AI analysis is complete, but the PDF report is not ready yet. '
              'Retry the status check in a moment.',
            ),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: () {
                setState(() {
                  _pollCount = 0;
                });
                _startPolling();
              },
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    } else {
      return _buildCard(
        title: 'Forensic Report',
        child: const Column(
          children: [
            LinearProgressIndicator(),
            SizedBox(height: 8),
            Text('AI result is ready. Report generation is still pending.'),
          ],
        ),
      );
    }
  }

  Widget _buildBlockchainCard() {
    switch (_blockchainStatus) {
      case 'confirmed':
        final txShort =
            _blockchainTxHash != null && _blockchainTxHash!.length > 16
            ? '${_blockchainTxHash!.substring(0, 12)}...${_blockchainTxHash!.substring(_blockchainTxHash!.length - 8)}'
            : (_blockchainTxHash ?? '-');
        final blockDisplay = _blockNumber?.toString() ?? '-';

        return _buildCard(
          title: 'Blockchain Verification',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.verified_user, color: Colors.green, size: 18),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Report hash anchored on DeepShield private chain.',
                      style: TextStyle(fontSize: 13),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'TX Hash: ',
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.grey[600],
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Expanded(
                    child: Text(
                      txShort,
                      style: const TextStyle(
                        fontSize: 11,
                        fontFamily: 'monospace',
                        color: Colors.white,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  Text(
                    'Block: ',
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.grey[600],
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Text(
                    blockDisplay,
                    style: const TextStyle(
                      fontSize: 11,
                      fontFamily: 'monospace',
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  Text(
                    'Chain: ',
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.grey[600],
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const Text(
                    'DeepShield Private Chain (EVM)',
                    style: TextStyle(fontSize: 11, color: Colors.white70),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                icon: const Icon(Icons.copy, size: 14),
                label: const Text(
                  'Copy Transaction Hash',
                  style: TextStyle(fontSize: 12),
                ),
                onPressed: _blockchainTxHash != null
                    ? () {
                        Clipboard.setData(
                          ClipboardData(text: _blockchainTxHash!),
                        );
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Transaction hash copied'),
                          ),
                        );
                      }
                    : null,
              ),
              const SizedBox(height: 8),
              Text(
                'This transaction proves the forensic report hash was '
                'recorded on-chain at the time shown in the PDF. '
                'Download the report to view the full verification record.',
                style: TextStyle(fontSize: 10, color: Colors.grey[500]),
              ),
            ],
          ),
        );
      case 'failed':
        return _buildCard(
          title: 'Blockchain Verification',
          child: const Row(
            children: [
              Icon(Icons.warning_amber, color: Colors.orange, size: 18),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Blockchain anchoring was unsuccessful. '
                  'The forensic report remains valid.',
                  style: TextStyle(fontSize: 13),
                ),
              ),
            ],
          ),
        );
      case 'pending':
      default:
        if (_pollCount >= _maxPolls) {
          return _buildCard(
            title: 'Blockchain Verification',
            child: const Text(
              'Verification status unavailable. '
              'Check the PDF report for anchoring details.',
              style: TextStyle(fontSize: 13),
            ),
          );
        }
        return _buildCard(
          title: 'Blockchain Verification',
          child: const Column(
            children: [
              LinearProgressIndicator(),
              SizedBox(height: 8),
              Text(
                'Anchoring to blockchain...',
                style: TextStyle(fontSize: 13),
              ),
            ],
          ),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final result = widget.result;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Analysis Result'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: TweenAnimationBuilder<double>(
        tween: Tween(begin: 0, end: 1),
        duration: const Duration(milliseconds: 450),
        curve: Curves.easeOutCubic,
        builder: (context, value, child) {
          return Opacity(
            opacity: value,
            child: Transform.translate(
              offset: Offset(0, (1 - value) * 12),
              child: child,
            ),
          );
        },
        child: SingleChildScrollView(
          padding: AppSpacing.screenPadding,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildVerdictHeader(context, result),
              const SizedBox(height: AppSpacing.md),
              _buildOutcomeExplanation(context, result),
              const SizedBox(height: AppSpacing.md),
              _buildStatusSummary(context),
              const SizedBox(height: AppSpacing.lg),
              _buildMainCard(context, result),
              const SizedBox(height: AppSpacing.lg),
              if (result.type == 'video') ...[
                _buildVideoAnalysis(context, result),
                const SizedBox(height: AppSpacing.lg),
              ],
              _buildForensicHistory(context, result),
              const SizedBox(height: AppSpacing.lg),
              PrimaryButton(
                label: _reportReady ? 'View full PDF report' : 'Report pending',
                icon: const Icon(Icons.picture_as_pdf, color: Colors.white),
                onPressed: _reportReady
                    ? () {
                        final summary = ReportSummary(
                          result: _currentResult(),
                          mediaType: result.mediaItem.type,
                          duration: '00:20',
                          size: '2.4 MB',
                          qrPlaceholderAsset:
                              'assets/vectors/qr_placeholder.svg',
                          heatmapAsset: '',
                        );
                        Navigator.pushNamed(
                          context,
                          AppRoutes.report,
                          arguments: summary,
                        );
                      }
                    : null,
              ),
              const SizedBox(height: AppSpacing.md),
              PrimaryButton(
                label: 'Verify on blockchain',
                icon: const Icon(Icons.verified_outlined, color: Colors.white),
                onPressed: () =>
                    _showBlockchainSheet(context, _currentResult()),
              ),
              const SizedBox(height: AppSpacing.md),
              PrimaryButton(
                label: 'Analyze another media',
                icon: const Icon(Icons.replay_outlined, color: Colors.white),
                onPressed: () => Navigator.pushNamedAndRemoveUntil(
                  context,
                  AppRoutes.home,
                  (route) => false,
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
              _buildMetadataSection(context, result),
              const SizedBox(height: AppSpacing.lg),
              _buildForensicReportCard(),
              const SizedBox(height: AppSpacing.lg),
              _buildBlockchainCard(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildVerdictHeader(BuildContext context, AnalysisResult result) {
    final displayConfidence = result.displayConfidence;
    final confidence = _confidenceLabel(displayConfidence);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Expanded(
              child: Text(
                result.prediction,
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: result.verdictColor,
                ),
                maxLines: 2,
              ),
            ),
            TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: displayConfidence),
              duration: const Duration(milliseconds: 900),
              curve: Curves.easeOutCubic,
              builder: (context, value, _) {
                return Text(
                  '${(value * 100).toStringAsFixed(1)}%',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
                );
              },
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          '$confidence confidence - ${_confidenceDescription(displayConfidence)}',
          style: Theme.of(
            context,
          ).textTheme.titleSmall?.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(
          'Manipulation band: ${result.band}',
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: AppSpacing.sm),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: TweenAnimationBuilder<double>(
            tween: Tween(begin: 0, end: displayConfidence),
            duration: const Duration(milliseconds: 900),
            curve: Curves.easeOutCubic,
            builder: (context, value, _) {
              return LinearProgressIndicator(
                value: value,
                backgroundColor: AppColors.border,
                color: result.verdictColor,
                minHeight: 8,
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildOutcomeExplanation(BuildContext context, AnalysisResult result) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: AppRadii.card,
        border: Border.all(color: AppColors.border),
      ),
      child: Text(
        _verdictExplanation(result),
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
          color: AppColors.textPrimary,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _buildStatusSummary(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _StatusPill(
            label: 'Report',
            value: _reportReady ? 'Ready' : 'Pending',
            color: _reportReady ? Colors.green : Colors.orange,
          ),
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          child: _StatusPill(
            label: 'Blockchain',
            value: _blockchainStatus == 'confirmed'
                ? 'Verified'
                : _blockchainStatus == 'failed'
                ? 'Failed'
                : 'Pending',
            color: _blockchainStatus == 'confirmed'
                ? Colors.green
                : _blockchainStatus == 'failed'
                ? Colors.orange
                : AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  String _confidenceLabel(double confidence) {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.5) return 'Medium';
    return 'Low';
  }

  String _confidenceDescription(double confidence) {
    if (confidence >= 0.8) {
      return 'the model found a strong signal in the media.';
    }
    if (confidence >= 0.5) {
      return 'the model found a noticeable signal, but review is recommended.';
    }
    return 'the model found weak evidence, so treat this as inconclusive.';
  }

  String _verdictExplanation(AnalysisResult result) {
    switch (result.verdict) {
      case Verdict.authentic:
        return 'This media appears likely authentic. The model found a low manipulation signal.';
      case Verdict.suspected:
        if (result.prediction.toLowerCase().contains('ai-generated')) {
          return 'This media is classified as AI-generated based on the AI generation signal.';
        }
        return 'This media shows signs of manipulation.';
      case Verdict.inconclusive:
        return 'The result is unclear. The score falls between the real and fake thresholds.';
    }
  }

  Widget _buildMainCard(BuildContext context, AnalysisResult result) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.cardOverlay,
        borderRadius: AppRadii.card,
        boxShadow: const [AppShadows.soft],
        border: Border.all(color: AppColors.subtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            result.filename,
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: AppSpacing.md),
          Container(
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: AppRadii.card,
              border: Border.all(color: AppColors.border),
            ),
            child: SwitchListTile.adaptive(
              value: _showHeatmap,
              onChanged: result.heatmapUrl == null || result.heatmapUrl!.isEmpty
                  ? null
                  : (value) => setState(() => _showHeatmap = value),
              title: const Text('Show heatmap evidence'),
              subtitle: Text(
                result.heatmapUrl == null || result.heatmapUrl!.isEmpty
                    ? 'No heatmap was returned for this analysis.'
                    : 'Highlights regions the model considered during analysis.',
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
              ),
            ),
          ),
          if (_showHeatmap) ...[
            const SizedBox(height: AppSpacing.md),
            ClipRRect(
              borderRadius: AppRadii.card,
              child: Container(
                height: 200,
                width: double.infinity,
                color: AppColors.border.withOpacity(0.2),
                child: _buildHeatmapImage(result.heatmapUrl),
              ),
            ),
          ],
          const SizedBox(height: AppSpacing.md),
          if (result.details != null &&
              result.details!['model'] == 'ucf_and_xception') ...[
            Text(
              'Model Details',
              style: Theme.of(
                context,
              ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: AppSpacing.sm),
            Builder(
              builder: (context) {
                final fusion =
                    result.details!['fusion_weights'] as Map<String, dynamic>?;
                if (fusion == null) return const SizedBox.shrink();
                final ucfW = (fusion['ucf'] as num?)?.toDouble() ?? 0.8;
                final xcepW = (fusion['xception'] as num?)?.toDouble() ?? 0.2;
                return Text(
                  'The final score combines video-temporal and visual-frame signals (${(ucfW * 100).toInt()}% / ${(xcepW * 100).toInt()}%).',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                );
              },
            ),
            const SizedBox(height: AppSpacing.md),
          ],
          if (result.details != null) ...[
            Text(
              'Signals',
              style: Theme.of(
                context,
              ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: AppSpacing.sm),
            if (result.aiProbability != null)
              _metaRow(
                'AI-generated signal',
                '${(result.aiProbability! * 100).toStringAsFixed(1)}%',
              ),
            if (result.manipulationProbability != null)
              _metaRow(
                'Manipulation signal',
                '${(result.manipulationProbability! * 100).toStringAsFixed(1)}%',
              ),
            if (result.thresholds != null) ...[
              _metaRow(
                'Real threshold',
                '${(((result.thresholds!['real'] as num?)?.toDouble() ?? 0.0) * 100).toStringAsFixed(0)}%',
              ),
              _metaRow(
                'Fake threshold',
                '${(((result.thresholds!['fake'] as num?)?.toDouble() ?? 0.0) * 100).toStringAsFixed(0)}%',
              ),
            ],
            const SizedBox(height: AppSpacing.md),
          ],
          Text(
            result.explanation,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }

  Widget _buildVideoAnalysis(BuildContext context, AnalysisResult result) {
    if (result.details == null) return const SizedBox.shrink();

    final frameCount = result.details!['frame_count'];
    final xception =
        result.details!['xception_metrics'] as Map<String, dynamic>?;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: AppRadii.card,
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.videocam_outlined, color: AppColors.primary),
              const SizedBox(width: AppSpacing.sm),
              Text(
                'Video Analysis Tracker',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          if (frameCount != null)
            _metaRow('Analyzed frames', '$frameCount evaluated'),
          if (xception != null) ...[
            _metaRow(
              'Mean frame confidence',
              '${(((xception['mean'] as num?)?.toDouble() ?? 0.0) * 100.0).toStringAsFixed(1)}%',
            ),
            _metaRow(
              'Max frame confidence',
              '${(((xception['max'] as num?)?.toDouble() ?? 0.0) * 100.0).toStringAsFixed(1)}%',
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildForensicHistory(BuildContext context, AnalysisResult result) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: result.isDuplicate ? AppColors.surface : AppColors.cardOverlay,
        borderRadius: AppRadii.card,
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Forensic History',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: AppSpacing.sm),
          if (!result.isDuplicate && result.priorAnalyses.length <= 1)
            Text(
              'First submission - no prior history for this file.',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
            )
          else ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              margin: const EdgeInsets.only(bottom: AppSpacing.md),
              decoration: BoxDecoration(
                color: Colors.orange.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.orange.withOpacity(0.3)),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.warning_amber_rounded,
                    color: Colors.orange,
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'This file has been submitted before.',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.orange,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            ..._buildHistoryList(result),
          ],
        ],
      ),
    );
  }

  List<Widget> _buildHistoryList(AnalysisResult result) {
    final list = result.priorAnalyses.where((e) => e.id != result.id).toList();
    if (list.isEmpty) return [];

    final formatter = DateFormat('MMM d, y, h:mm a');

    return list.map((item) {
      final isExpanded = _expandedHistoryItems.contains(item.id);

      return Container(
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
          color: AppColors.cardOverlay,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.subtle),
        ),
        child: InkWell(
          onTap: () {
            setState(() {
              if (isExpanded) {
                _expandedHistoryItems.remove(item.id);
              } else {
                _expandedHistoryItems.add(item.id);
              }
            });
          },
          borderRadius: BorderRadius.circular(8),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      item.prediction,
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    Text(
                      '${(item.confidence * 100).toStringAsFixed(1)}%',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      formatter.format(item.createdAt),
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    Icon(
                      isExpanded ? Icons.expand_less : Icons.expand_more,
                      size: 16,
                    ),
                  ],
                ),
                if (isExpanded) ...[
                  const SizedBox(height: 12),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      height: 140,
                      width: double.infinity,
                      color: AppColors.border.withOpacity(0.2),
                      child: _buildHeatmapImage(item.heatmapUrl),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      );
    }).toList();
  }

  Widget _buildHeatmapImage(String? url) {
    if (url == null || url.isEmpty) {
      return const Center(
        child: Text(
          'Heatmap unavailable',
          style: TextStyle(color: AppColors.textSecondary),
        ),
      );
    }
    return Image.network(
      url,
      fit: BoxFit.cover,
      errorBuilder: (context, error, stackTrace) => const Center(
        child: Text(
          'Heatmap unavailable',
          style: TextStyle(color: AppColors.textSecondary),
        ),
      ),
    );
  }

  Widget _buildMetadataSection(BuildContext context, AnalysisResult result) {
    final formatter = DateFormat('MMM d, y, h:mm a');
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: AppRadii.card,
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Metadata', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: AppSpacing.sm),
          _metaRow('Analyzed on', formatter.format(result.createdAt)),
          _metaRow('Media type', result.type),
          _metaRow(
            'Blockchain hash',
            _blockchainTxHash != null
                ? _shortTxHash(_blockchainTxHash)
                : 'Pending...',
          ),
        ],
      ),
    );
  }

  String _shortTxHash(String? hash) {
    if (hash == null || hash.isEmpty) {
      return 'Pending...';
    }
    if (hash.length <= 16) {
      return hash;
    }
    return '${hash.substring(0, 10)}...${hash.substring(hash.length - 6)}';
  }

  Widget _metaRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
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
              style: const TextStyle(fontWeight: FontWeight.w600),
              textAlign: TextAlign.right,
            ),
          ),
        ],
      ),
    );
  }

  void _showBlockchainSheet(BuildContext context, AnalysisResult result) {
    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (_) {
        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.shield_outlined, color: AppColors.primary),
                  const SizedBox(width: AppSpacing.sm),
                  Text(
                    'Blockchain Verification',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.md),
              _metaRow('Status', _blockchainStatus),
              _metaRow('Hash', _shortTxHash(_blockchainTxHash)),
              _metaRow(
                'Timestamp',
                DateFormat('MMM d, h:mm a').format(result.createdAt),
              ),
              const SizedBox(height: AppSpacing.md),
              PrimaryButton(
                label: 'Close',
                onPressed: () => Navigator.pop(context),
                fullWidth: true,
              ),
            ],
          ),
        );
      },
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: AppRadii.card,
        border: Border.all(color: color.withOpacity(0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 2),
          Text(
            value,
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
