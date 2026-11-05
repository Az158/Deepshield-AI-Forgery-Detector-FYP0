/// Request wrapper for deepfake analysis calls (image/video only).
class DeepfakeRequest {
  DeepfakeRequest({
    required this.filePath,
    required this.mediaTitle,
    required this.mediaType,
  });

  /// Absolute path to the picked file.
  final String filePath;

  /// Friendly title shown in UI/history.
  final String mediaTitle;

  /// High-level media type label (image / video). Mapped to the image endpoint.
  final String mediaType;
}
