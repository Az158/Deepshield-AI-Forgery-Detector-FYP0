class HealthStatus {
  HealthStatus({
    required this.status,
    required this.ucfLoaded,
    required this.xceptionLoaded,
    required this.aiService,
    required this.ucfReported,
    required this.xceptionReported,
    this.lastChecked,
  });

  final String status;
  final bool ucfLoaded;
  final bool xceptionLoaded;
  final String aiService;
  final bool ucfReported;
  final bool xceptionReported;
  final DateTime? lastChecked;

  factory HealthStatus.fromJson(Map<String, dynamic> json) {
    final hasUcfLoaded = json.containsKey('ucf_loaded');
    final hasXceptionLoaded = json.containsKey('xception_loaded');
    final hasGenericModelLoaded = json.containsKey('model_loaded');
    final genericModelLoaded = json['model_loaded'] as bool?;

    return HealthStatus(
      status: json['status'] as String? ?? 'unknown',
      ucfLoaded:
          json['ucf_loaded'] as bool? ?? genericModelLoaded ?? false,
      xceptionLoaded: json['xception_loaded'] as bool? ?? false,
      aiService:
          json['ai_service'] as String? ??
          json['service'] as String? ??
          'Unknown',
      ucfReported: hasUcfLoaded || hasGenericModelLoaded,
      xceptionReported: hasXceptionLoaded,
      lastChecked: DateTime.now(),
    );
  }
}
