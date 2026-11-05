import 'dart:collection';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:open_file/open_file.dart';
import 'package:path_provider/path_provider.dart';

import '../environment.dart';
import 'authenticated_http.dart';

class ReportDownloadException implements Exception {
  const ReportDownloadException(this.message);

  final String message;

  @override
  String toString() => message;
}

Future<void> downloadAndOpenReport({
  required BuildContext context,
  required String reportUrl,
  required String token,
}) async {
  final candidates = _buildDownloadCandidates(reportUrl);
  Object? lastError;

  for (final candidate in candidates) {
    try {
      debugPrint('[ReportDownloader] trying $candidate');
      final response = await http.get(
        Uri.parse(candidate),
        headers: {'Authorization': 'Bearer $token'},
      ).timeout(const Duration(seconds: 30));

      debugPrint(
        '[ReportDownloader] status=${response.statusCode} '
        'contentType=${response.headers['content-type']}',
      );

      if (response.statusCode == 401) {
        await handleUnauthorized(context);
        throw const ReportDownloadException('Session expired');
      }

      if (response.statusCode != 200 || !_looksLikePdf(response)) {
        lastError = ReportDownloadException(
          'Download failed from $candidate: ${response.statusCode}',
        );
        continue;
      }

      await _saveAndOpen(response.bodyBytes);
      return;
    } catch (error) {
      lastError = error;
    }
  }

  throw ReportDownloadException(
    lastError?.toString() ?? 'Could not download the report.',
  );
}

List<String> _buildDownloadCandidates(String rawUrl) {
  final normalized = rawUrl.trim();
  if (normalized.isEmpty) {
    return const [];
  }

  final baseUrl = _resolveBaseUrl(
    Environment.aiServiceUrl,
  ).replaceAll(RegExp(r'/+$'), '');
  final candidates = <String>[];

  Uri? uri;
  try {
    uri = Uri.parse(normalized);
  } catch (_) {
    uri = null;
  }

  if (uri != null && uri.hasScheme) {
    candidates.add(uri.toString());
  } else {
    final path = normalized.startsWith('/') ? normalized : '/$normalized';
    candidates.add('$baseUrl$path');
  }

  final filename = _extractFilename(uri, normalized);
  if (filename != null && filename.isNotEmpty) {
    candidates.add('$baseUrl/outputs/${Uri.encodeComponent(filename)}');
  }

  return LinkedHashSet<String>.from(candidates).toList();
}

String? _extractFilename(Uri? uri, String rawUrl) {
  if (uri != null && uri.pathSegments.isNotEmpty) {
    return uri.pathSegments.last;
  }

  final cleaned = rawUrl.split('?').first.split('#').first;
  final parts = cleaned.split('/').where((part) => part.isNotEmpty).toList();
  if (parts.isEmpty) {
    return null;
  }
  return parts.last;
}

bool _looksLikePdf(http.Response response) {
  final contentType = response.headers['content-type']?.toLowerCase() ?? '';
  if (contentType.contains('application/pdf')) {
    return true;
  }

  final bytes = response.bodyBytes;
  return bytes.length >= 4 &&
      bytes[0] == 0x25 &&
      bytes[1] == 0x50 &&
      bytes[2] == 0x44 &&
      bytes[3] == 0x46;
}

Future<void> _saveAndOpen(List<int> bytes) async {
  final dir = await getTemporaryDirectory();
  final filename =
      'deepshield_report_${DateTime.now().millisecondsSinceEpoch}.pdf';
  final file = File('${dir.path}/$filename');
  await file.writeAsBytes(bytes);

  final result = await OpenFile.open(file.path);
  if (result.type != ResultType.done) {
    throw ReportDownloadException('Could not open PDF: ${result.message}');
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
