import 'package:flutter/material.dart';

import '../data/services/auth_service.dart';
import '../data/services/bootstrap_service.dart';

/// Global app state for auth + onboarding flags (in-memory only).
class AppState extends ChangeNotifier {
  AppState({
    required AuthService authService,
    required BootstrapService bootstrapService,
  })  : _authService = authService,
        _bootstrapService = bootstrapService;

  final AuthService _authService;
  final BootstrapService _bootstrapService;

  bool _isLoading = false;

  bool get isLoading => _isLoading;
  bool get isLoggedIn => _authService.isLoggedIn;
  String get userEmail => _authService.email;
  String get userName => _authService.name;

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    notifyListeners();
    final result = await _authService.login(email: email, password: password);
    _isLoading = false;
    await _bootstrapService.completeFirstLaunch();
    notifyListeners();
    return result;
  }

  Future<bool> signUp(String name, String email, String password) async {
    _isLoading = true;
    notifyListeners();
    final result =
        await _authService.signUp(name: name, email: email, password: password);
    _isLoading = false;
    await _bootstrapService.completeFirstLaunch();
    notifyListeners();
    return result;
  }

  Future<void> logout() async {
    _isLoading = true;
    notifyListeners();
    await _authService.logout();
    _isLoading = false;
    notifyListeners();
  }

  Future<bool> isFirstLaunch() => _bootstrapService.isFirstLaunch();
  Future<bool> isLoggedInFuture() => _bootstrapService.isLoggedIn();
}
