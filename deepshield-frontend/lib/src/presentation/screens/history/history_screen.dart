import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../core/constants.dart';
import '../../../core/environment.dart';
import '../../../core/theme.dart';
import '../../../core/utils/authenticated_http.dart';
import '../../../core/utils/service_locator.dart';
import '../../../routes/app_router.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<Map<String, dynamic>> _analyses = [];
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _fetchHistory();
  }

  Future<void> _fetchHistory() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final authProvider = ServiceLocator.authProvider;
      final token = authProvider.token;

      if (token == null || token.isEmpty) {
        setState(() {
          _isLoading = false;
          _errorMessage = 'Your session has expired. Log in again to view history.';
        });
        return;
      }

      final baseUrl = _resolveBaseUrl(
        Environment.aiServiceUrl,
      ).replaceAll(RegExp(r'/+$'), '');
      final response = await authenticatedGet(
        '$baseUrl/analyses/history',
        token,
        context,
      );

      if (!mounted) {
        return;
      }

      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body);
        final raw = decoded is Map<String, dynamic>
            ? (decoded['analyses'] ?? decoded['items'] ?? decoded['data'])
            : decoded;
        final List<dynamic> analysesRaw = raw is List ? raw : <dynamic>[];

        setState(() {
          _analyses = analysesRaw
              .whereType<Map<String, dynamic>>()
              .map((item) => Map<String, dynamic>.from(item))
              .toList()
            ..sort((a, b) {
              final aDate = DateTime.tryParse(a['created_at']?.toString() ?? '');
              final bDate = DateTime.tryParse(b['created_at']?.toString() ?? '');
              return (bDate ?? DateTime(0)).compareTo(aDate ?? DateTime(0));
            });
          _isLoading = false;
        });
      } else {
        setState(() {
          _isLoading = false;
          _errorMessage =
              'History could not be loaded. Check the backend, then retry.';
        });
      }
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _isLoading = false;
        _errorMessage =
            'Could not reach the server. Check your connection and retry.';
      });
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

  String _formatDate(String? rawValue) {
    if (rawValue == null || rawValue.isEmpty) {
      return 'Unknown date';
    }
    try {
      final dt = DateTime.parse(rawValue).toLocal();
      return DateFormat('dd MMM yyyy, HH:mm').format(dt);
    } catch (_) {
      return 'Unknown date';
    }
  }

  String _formatConfidence(dynamic confidenceValue) {
    final parsed = (confidenceValue as num?)?.toDouble() ?? 0.0;
    final normalized = parsed <= 1 ? parsed * 100 : parsed;
    return '${normalized.toStringAsFixed(1)}%';
  }

  String _displayConfidenceFor(Map<String, dynamic> item) {
    final prediction = item['prediction']?.toString().toLowerCase() ?? '';
    final rawConfidence = (item['confidence'] as num?)?.toDouble() ?? 0.0;
    final confidence = rawConfidence > 1 ? rawConfidence / 100 : rawConfidence;
    final details = item['details'];

    if (prediction.contains('ai-generated') &&
        details is Map<String, dynamic> &&
        details['ai_prob'] is num) {
      return _formatConfidence(details['ai_prob']);
    }

    if (prediction.contains('authentic')) {
      return '${((1 - confidence).clamp(0.0, 1.0) * 100).toStringAsFixed(1)}%';
    }

    return _formatConfidence(confidence);
  }

  String _statusFor(Map<String, dynamic> item) {
    final prediction = item['prediction']?.toString() ?? '';
    if (prediction.isEmpty || prediction == 'Unknown') {
      return 'Pending';
    }
    return 'Analyzed';
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'Analyzed':
        return Colors.green;
      case 'Pending':
      default:
        return AppColors.textSecondary;
    }
  }

  String _statusHelp(String status) {
    switch (status) {
      case 'Analyzed':
        return 'AI classification is available; report or blockchain may still be pending.';
      case 'Pending':
      default:
        return 'Analysis is still processing. Pull to refresh.';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('History')),
      body: Padding(padding: AppSpacing.screenPadding, child: _buildBody()),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              _errorMessage!,
              style: const TextStyle(color: AppColors.textSecondary),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.md),
            ElevatedButton(
              onPressed: _fetchHistory,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_analyses.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.history_toggle_off_rounded,
              color: AppColors.textSecondary,
              size: 44,
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              'No analyses yet.',
              style: Theme.of(context).textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.xs),
            const Text(
              'Upload your first file to get started.',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.md),
            ElevatedButton.icon(
              onPressed: () => Navigator.pushNamedAndRemoveUntil(
                context,
                AppRoutes.home,
                (route) => false,
              ),
              icon: const Icon(Icons.upload_file_rounded),
              label: const Text('Start analysis'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _fetchHistory,
      child: ListView.builder(
        itemCount: _analyses.length,
        itemBuilder: (context, index) {
          final item = _analyses[index];
          final filename = item['filename']?.toString() ?? 'Unknown file';
          final label = item['prediction']?.toString() ?? 'Unknown';
          final confidence = _displayConfidenceFor(item);
          final createdAt = _formatDate(item['created_at']?.toString());
          final mediaType =
              item['type']?.toString() ??
              item['media_type']?.toString() ??
              'unknown';
          final status = _statusFor(item);
          final statusColor = _statusColor(status);

          return Container(
            margin: const EdgeInsets.only(bottom: AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.cardOverlay,
              borderRadius: AppRadii.card,
              border: Border.all(color: AppColors.border),
            ),
            child: ListTile(
              contentPadding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.md,
                vertical: AppSpacing.sm,
              ),
              title: Text(
                filename,
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              subtitle: Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Label: $label'),
                    Text('Confidence: $confidence'),
                    Text('Status: $status'),
                    Text(
                      _statusHelp(status),
                      style: const TextStyle(color: AppColors.textSecondary),
                    ),
                    Text('Created: $createdAt'),
                    Text('Type: $mediaType'),
                  ],
                ),
              ),
              trailing: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.12),
                  borderRadius: AppRadii.card,
                  border: Border.all(color: statusColor.withOpacity(0.35)),
                ),
                child: Text(
                  status,
                  style: TextStyle(
                    color: statusColor,
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                  ),
                ),
              ),
              onTap: status == 'Pending'
                  ? () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text(
                            'This analysis is still processing. Pull to refresh, then reopen it.',
                          ),
                        ),
                      );
                    }
                  : () => Navigator.pushNamed(
                      context,
                      AppRoutes.result,
                      arguments: {
                        ...item,
                        'type': mediaType,
                      },
                    ),
            ),
          );
        },
      ),
    );
  }
}
