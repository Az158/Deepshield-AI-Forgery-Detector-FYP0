import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../src/core/environment.dart';
import '../src/data/models/analysis_result.dart';
import '../src/data/models/media_item.dart';
import '../models/analysis_status_result.dart';

class AnalysisService {
  Future<List<AnalysisResult>> fetchHistory(String token) async {
    final uri = _buildUri('/analyses/history');

    try {
      // debug: log the exact URI being requested for polling
      // ignore: avoid_print
      print('AnalysisService.fetchAnalysisStatus GET $uri');
      final response = await http
          .get(uri, headers: {'Authorization': 'Bearer $token'})
          .timeout(const Duration(seconds: 8));

      if (response.statusCode == 404) {
        return const [];
      }

      if (response.statusCode != 200) {
        return const [];
      }

      final decoded = jsonDecode(response.body);
      final items = decoded is List
          ? decoded
          : (decoded is Map<String, dynamic>
                ? (decoded['items'] ??
                      decoded['analyses'] ??
                      decoded['data'] ??
                      const [])
                : const []);

      if (items is! List) {
        return const [];
      }

      return items
          .whereType<Map<String, dynamic>>()
          .map(
            (json) => AnalysisResult.fromJson(
              json,
              MediaItem(
                id: json['id'] as String? ?? '',
                title:
                    json['media_title'] as String? ??
                    json['filename'] as String? ??
                    'Unknown',
                url: json['media_url'] as String? ?? '',
                type: json['type'] as String? ?? 'image',
                thumbnailAsset: 'assets/images/logo.png',
              ),
            ),
          )
          .toList();
    } on TimeoutException {
      return const [];
    } on SocketException {
      return const [];
    } catch (_) {
      return const [];
    }
  }

  Future<AnalysisStatusResult> fetchAnalysisStatus(
    String analysisId,
    String token,
  ) async {
    if (analysisId.trim().isEmpty) {
      return const AnalysisStatusResult.failure(errorMessage: 'not_found');
    }
    final uri = _buildUri('/analyses/$analysisId');

    try {
      final response = await http
          .get(uri, headers: {'Authorization': 'Bearer $token'})
          .timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return AnalysisStatusResult.success(
          reportUrl: data['report_url'] as String? ?? data['pdf_url'] as String?,
          blockchainStatus: data['blockchain_status'] as String?,
          polygonUrl: data['polygon_url'] as String?,
          blockchainTxHash: data['blockchain_tx_hash'] as String?,
        );
      }

      if (response.statusCode == 404) {
        // Backend may not expose the polling endpoint yet; keep polling safely.
        return const AnalysisStatusResult.failure(errorMessage: 'not_found');
      }

      return const AnalysisStatusResult.failure(errorMessage: 'network_error');
    } on TimeoutException {
      return const AnalysisStatusResult.failure(errorMessage: 'network_error');
    } on SocketException {
      return const AnalysisStatusResult.failure(errorMessage: 'network_error');
    } catch (_) {
      return const AnalysisStatusResult.failure(errorMessage: 'network_error');
    }
  }

  Uri _buildUri(String path) {
    final resolved = _resolveBaseUrl(
      Environment.aiServiceUrl,
    ).replaceAll(RegExp(r'/+$'), '');
    final normalizedPath = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$resolved$normalizedPath');
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
}
