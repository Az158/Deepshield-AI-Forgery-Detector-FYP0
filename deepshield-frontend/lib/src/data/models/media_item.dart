/// Represents media being analyzed (fake data for MVP).
class MediaItem {
  MediaItem({
    required this.id,
    required this.title,
    required this.url,
    required this.type,
    this.thumbnailAsset,
  });

  final String id;
  final String title;
  final String url;
  final String type; // image, video, link
  final String? thumbnailAsset;
}
