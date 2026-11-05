import '../../../providers/auth_provider.dart';
import '../../../providers/analysis_status_provider.dart';
import '../../../services/auth_service.dart';
import '../../../services/auth_storage.dart';
import '../../../services/analysis_service.dart';
import '../../data/services/fake_analysis_service.dart';
import '../../data/services/history_service.dart';
import '../../data/services/deepfake_service.dart';

/// Simple manual service locator for the MVP.
class ServiceLocator {
  ServiceLocator._();

  static final authService = AuthService();
  static final authStorage = AuthStorage();
  static final authProvider = AuthProvider(
    authService: authService,
    authStorage: authStorage,
  );
  static final historyService = HistoryService();
  static final analysisService = AnalysisService();
  static final analysisStatusProvider = AnalysisStatusProvider(
    analysisService: analysisService,
  );
  static final fakeAnalysisService = FakeAnalysisService(
    historyService: historyService,
  );
  static final deepfakeService = DeepfakeService(
    historyService: historyService,
    authProvider: authProvider,
  );
}
