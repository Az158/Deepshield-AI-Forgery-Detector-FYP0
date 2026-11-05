import 'auth_service.dart';

/// Simple bootstrap helper to check onboarding + auth.
class BootstrapService {
  BootstrapService({required this.authService});

  final AuthService authService;
  bool _isFirstLaunch = true;

  Future<bool> isFirstLaunch() async {
    await Future.delayed(const Duration(milliseconds: 200));
    return _isFirstLaunch;
  }

  Future<void> completeFirstLaunch() async {
    _isFirstLaunch = false;
  }

  Future<bool> isLoggedIn() async {
    await Future.delayed(const Duration(milliseconds: 200));
    return authService.isLoggedIn;
  }
}
