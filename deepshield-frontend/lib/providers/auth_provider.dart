import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../services/auth_service.dart';
import '../services/auth_storage.dart';
import '../src/core/environment.dart';

class AuthProvider extends ChangeNotifier {
  AuthProvider({
    required AuthService authService,
    required AuthStorage authStorage,
  }) : _authService = authService,
       _authStorage = authStorage;

  static const _tokenKey = 'deepshield_token';
  static const _userIdKey = 'deepshield_user_id';
  static const _emailKey = 'deepshield_email';

  final AuthService _authService;
  final AuthStorage _authStorage;

  bool _isLoggedIn = false;
  bool _isLoading = false;
  String? _errorMessage;
  String? _signupSuccessMessage;
  String? _token;
  String? _userId;
  String? _userEmail;

  bool get isLoggedIn => _isLoggedIn;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  String? get token => _token;
  String? get userId => _userId;
  String? get userEmail => _userEmail;
  String? get signupSuccessMessage => _signupSuccessMessage;

  String get userDisplayName {
    final email = _userEmail;
    if (email == null || email.isEmpty) {
      return 'DeepShield User';
    }
    return email.split('@').first;
  }

  Future<void> tryAutoLogin() async {
    try {
      final session = await _authStorage.loadSession();
      final token = session[_tokenKey];

      if (token == null) {
        _isLoggedIn = false;
        _token = null;
        _userId = null;
        _userEmail = null;
        notifyListeners();
        return;
      }

      final isValid = await _validateToken(token);

      if (isValid) {
        _token = token;
        _userId = session[_userIdKey];
        _userEmail = session[_emailKey];
        _isLoggedIn = true;
      } else {
        await _authStorage.clearSession();
        _isLoggedIn = false;
        _token = null;
        _userId = null;
        _userEmail = null;
      }
    } catch (_) {
      _isLoggedIn = false;
    }

    notifyListeners();
  }

  Future<bool> _validateToken(String token) async {
    try {
      final baseUrl = _resolveBaseUrl(
        Environment.aiServiceUrl,
      ).replaceAll(RegExp(r'/+$'), '');

      final response = await http
          .get(
            Uri.parse('$baseUrl/analyses/history'),
            headers: {'Authorization': 'Bearer $token'},
          )
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      // Network failures should not force logout.
      return true;
    }
  }

  Future<void> login(String email, String password) async {
    _isLoading = true;
    _errorMessage = null;
    _signupSuccessMessage = null;
    notifyListeners();

    final result = await _authService.login(email, password);

    if (result.success &&
        result.accessToken != null &&
        result.userId != null &&
        result.email != null) {
      _token = result.accessToken;
      _userId = result.userId;
      _userEmail = result.email;
      _isLoggedIn = true;
      await _authStorage.saveSession(_token!, _userId!, _userEmail!);
    } else {
      _errorMessage = result.errorMessage;
      _isLoggedIn = false;
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<void> signup(String email, String password) async {
    _isLoading = true;
    _errorMessage = null;
    _signupSuccessMessage = null;
    notifyListeners();

    final result = await _authService.signup(email, password);

    final message = result.errorMessage;
    if (message != null && message.startsWith('Account created')) {
      _signupSuccessMessage = message;
    } else {
      _errorMessage = message;
    }

    _isLoading = false;
    notifyListeners();
  }

  Future<void> logout() async {
    final activeToken = _token;
    await _authStorage.clearSession();
    _isLoggedIn = false;
    _isLoading = false;
    _token = null;
    _userId = null;
    _userEmail = null;
    _signupSuccessMessage = null;
    _errorMessage = null;
    notifyListeners();

    if (activeToken != null && activeToken.isNotEmpty) {
      _authService.logout(activeToken).catchError((_) {});
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

  void clearError() {
    if (_errorMessage == null) {
      return;
    }
    _errorMessage = null;
    notifyListeners();
  }

  void setError(String message) {
    _errorMessage = message;
    notifyListeners();
  }

  void clearSignupSuccessMessage() {
    if (_signupSuccessMessage == null) {
      return;
    }
    _signupSuccessMessage = null;
    notifyListeners();
  }
}
