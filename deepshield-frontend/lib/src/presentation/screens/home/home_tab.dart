import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../../core/constants.dart';
import '../../../core/theme.dart';
import '../../../core/utils/service_locator.dart';
import '../../../data/models/deepfake_request.dart';
import '../../../data/models/media_item.dart';
import '../../../routes/app_router.dart';
import '../../widgets/primary_button.dart';

/// Main verification screen. Uses local file upload to call deepfake APIs.
class HomeTab extends StatefulWidget {
  const HomeTab({super.key});

  @override
  State<HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends State<HomeTab> {
  String? _filePath;
  String? _fileName;
  int? _fileSize;
  bool _isPicking = false;

  bool _isHealthy = false;
  bool _healthCheckDone = false;
  String _healthMessage = 'Checking backend connection...';

  @override
  void initState() {
    super.initState();
    _checkHealth();
  }

  Future<void> _checkHealth() async {
    setState(() {
      _healthCheckDone = false;
      _healthMessage = 'Checking backend connection...';
    });

    try {
      await ServiceLocator.deepfakeService.checkHealth();
      if (!mounted) return;
      setState(() {
        _isHealthy = true;
        _healthMessage = 'Backend connected';
        _healthCheckDone = true;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _isHealthy = false;
        _healthMessage = 'Backend unreachable - analysis unavailable';
        _healthCheckDone = true;
      });
    }
  }

  Future<void> _pickFile() async {
    setState(() => _isPicking = true);
    FilePickerResult? result;
    try {
      result = await FilePicker.platform.pickFiles(
        allowMultiple: false,
        type: FileType.custom,
        allowedExtensions: const ['jpg', 'jpeg', 'png', 'webp', 'mp4', 'mov', 'avi'],
      );
    } finally {
      if (mounted) {
        setState(() => _isPicking = false);
      }
    }

    if (!mounted || result == null || result.files.single.path == null) {
      return;
    }

    final picked = result.files.single;
    final path = picked.path!;
    if (!_isSupportedFile(path)) {
      _showSnack('Unsupported file type. Use JPG, PNG, WEBP, MP4, MOV, or AVI.');
      return;
    }

    final size = picked.size > 0 ? picked.size : File(path).lengthSync();
    if (size > 50 * 1024 * 1024) {
      _showSnack('File exceeds the 50MB limit. Choose a smaller file.');
      return;
    }

    setState(() {
      _filePath = path;
      _fileName = picked.name;
      _fileSize = size;
    });
  }

  void _startAnalysis() {
    if (!_healthCheckDone) {
      _showSnack('Still checking the backend connection.');
      return;
    }
    if (!_isHealthy) {
      _showSnack('Backend is unreachable. Re-check the connection first.');
      return;
    }
    if (_filePath == null) {
      _showSnack('Upload a file to analyze.');
      return;
    }

    final isVideo = _isVideoFile(_filePath!);
    final media = MediaItem(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      title: _fileName ?? 'Uploaded media',
      url: _filePath!,
      type: isVideo ? 'video' : 'image',
      thumbnailAsset: 'assets/images/logo.png',
    );

    final request = DeepfakeRequest(
      filePath: _filePath!,
      mediaType: isVideo ? 'video' : 'image',
      mediaTitle: media.title,
    );

    Navigator.pushNamed(
      context,
      AppRoutes.analysisProgress,
      arguments: request,
    );
  }

  bool _isVideoFile(String path) {
    final lower = path.toLowerCase();
    const videoExts = ['.mp4', '.mov', '.avi'];
    return videoExts.any((ext) => lower.endsWith(ext));
  }

  bool _isSupportedFile(String path) {
    final lower = path.toLowerCase();
    const allowedExts = ['.jpg', '.jpeg', '.png', '.webp', '.mp4', '.mov', '.avi'];
    return allowedExts.any((ext) => lower.endsWith(ext));
  }

  void _showSnack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  String _formatFileSize(int? bytes) {
    if (bytes == null || bytes <= 0) {
      return 'Size unavailable';
    }
    final mb = bytes / (1024 * 1024);
    if (mb >= 1) {
      return '${mb.toStringAsFixed(1)} MB';
    }
    return '${(bytes / 1024).toStringAsFixed(0)} KB';
  }

  @override
  Widget build(BuildContext context) {
    final name = ServiceLocator.authProvider.userDisplayName;
    final canUpload = _healthCheckDone && _isHealthy;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'DeepShield',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
        ),
        actions: [
          const CircleAvatar(
            radius: 16,
            backgroundImage: AssetImage('assets/images/logo.png'),
          ),
          const SizedBox(width: 12),
        ],
      ),
      body: SingleChildScrollView(
        padding: AppSpacing.screenPadding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Welcome, $name!',
              style: Theme.of(context)
                  .textTheme
                  .headlineMedium
                  ?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 6),
            Text(
              'Verify content authenticity with AI analysis and report anchoring.',
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: AppSpacing.lg),
            _HealthBanner(
              isDone: _healthCheckDone,
              isHealthy: _isHealthy,
              message: _healthMessage,
              onRetry: _checkHealth,
            ),
            const SizedBox(height: AppSpacing.md),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppSpacing.lg),
              decoration: BoxDecoration(
                color: AppColors.cardOverlay,
                borderRadius: AppRadii.card,
                boxShadow: const [AppShadows.medium],
                border: Border.all(color: AppColors.subtle),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  PrimaryButton(
                    label: _isPicking ? 'Picking...' : 'Upload Media',
                    icon: const Icon(Icons.cloud_upload_outlined),
                    onPressed: (_isPicking || !canUpload) ? null : _pickFile,
                    isBusy: _isPicking,
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    canUpload
                        ? 'Supports JPG, PNG, WEBP, MP4, MOV, and AVI up to 50MB.'
                        : 'Connect to the backend before uploading media.',
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: AppColors.textSecondary),
                    textAlign: TextAlign.center,
                  ),
                  if (_filePath != null) ...[
                    const SizedBox(height: AppSpacing.md),
                    _SelectedFileCard(
                      fileName: _fileName ?? 'Selected media',
                      fileSize: _formatFileSize(_fileSize),
                      isVideo: _isVideoFile(_filePath!),
                      onRemove: () => setState(() {
                        _filePath = null;
                        _fileName = null;
                        _fileSize = null;
                      }),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.md),
                  PrimaryButton(
                    label: 'Analyze File',
                    icon: const Icon(Icons.search),
                    onPressed: canUpload && _filePath != null ? _startAnalysis : null,
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    'Your media is sent securely to the configured analysis backend.',
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: AppColors.textSecondary),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HealthBanner extends StatelessWidget {
  const _HealthBanner({
    required this.isDone,
    required this.isHealthy,
    required this.message,
    required this.onRetry,
  });

  final bool isDone;
  final bool isHealthy;
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final color = !isDone
        ? AppColors.textSecondary
        : isHealthy
            ? Colors.green
            : Colors.red;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: AppRadii.card,
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Icon(
            !isDone
                ? Icons.sync_rounded
                : isHealthy
                    ? Icons.check_circle_outline
                    : Icons.error_outline,
            color: color,
            size: 20,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: color,
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
          if (isDone && !isHealthy)
            TextButton(
              onPressed: onRetry,
              child: const Text('Retry'),
            ),
        ],
      ),
    );
  }
}

class _SelectedFileCard extends StatelessWidget {
  const _SelectedFileCard({
    required this.fileName,
    required this.fileSize,
    required this.isVideo,
    required this.onRemove,
  });

  final String fileName;
  final String fileSize;
  final bool isVideo;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: AppRadii.card,
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Icon(
            isVideo ? Icons.videocam_outlined : Icons.image_outlined,
            color: AppColors.primary,
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  fileName,
                  style: Theme.of(context).textTheme.titleSmall,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  fileSize,
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: AppColors.textSecondary),
                ),
              ],
            ),
          ),
          IconButton(
            tooltip: 'Remove file',
            onPressed: onRemove,
            icon: const Icon(Icons.close_rounded),
          ),
        ],
      ),
    );
  }
}
