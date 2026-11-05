class AnalysisStatusResult {
  const AnalysisStatusResult.success({
    required this.reportUrl,
    required this.blockchainStatus,
    required this.polygonUrl,
    required this.blockchainTxHash,
  }) : success = true,
       errorMessage = null;

  const AnalysisStatusResult.failure({required this.errorMessage})
    : success = false,
      reportUrl = null,
      blockchainStatus = null,
      polygonUrl = null,
      blockchainTxHash = null;

  final bool success;
  final String? reportUrl;
  final String? blockchainStatus;
  final String? polygonUrl;
  final String? blockchainTxHash;
  final String? errorMessage;
}
