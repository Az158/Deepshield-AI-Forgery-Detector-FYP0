import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../models/auth_result.dart';
import '../src/core/environment.dart';

class AuthService {
  Future<AuthResult> signup(String email, String password) async {
    final uri = _buildUri('/auth/signup');

    try {
      final response = await http
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'email': email, 'password': password}),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 201) {
        return const AuthResult.failure(
          errorMessage:
              'Account created! Please check your email to verify your account before logging in.',
        );
      }

      if (response.statusCode == 400) {
        return const AuthResult.failure(
          errorMessage: 'An account with this email already exists.',
        );
      }

      if (response.statusCode == 422) {
        // Parse backend validation details to consume structured errors.
        try {
          final body = jsonDecode(response.body) as Map<String, dynamic>;
          final detail = body['detail'];
          if (detail == null) {
            // no-op
          }
        } catch (_) {
          // no-op
        }
        return const AuthResult.failure(
          errorMessage:
              'Please enter a valid email and a password of at least 8 characters.',
        );
      }

      return const AuthResult.failure(
        errorMessage: 'Could not complete signup. Please try again.',
      );
    } on TimeoutException catch (_) {
      return const AuthResult.failure(
        errorMessage:
            'Could not reach the server. Please check your connection.',
      );
    } on SocketException catch (_) {
      return const AuthResult.failure(
        errorMessage:
            'Could not reach the server. Please check your connection.',
      );
    } catch (_) {
      return const AuthResult.failure(
        errorMessage: 'Could not complete signup. Please try again.',
      );
    }
  }

  Future<AuthResult> login(String email, String password) async {
    final uri = _buildUri('/auth/login');

    try {
      final response = await http
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'email': email, 'password': password}),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return AuthResult.success(
          accessToken: data['access_token'] as String?,
          userId: data['user_id'] as String?,
          email: data['email'] as String?,
        );
      }

      if (response.statusCode == 401) {
        return const AuthResult.failure(
          errorMessage: 'Invalid email or password.',
        );
      }

      return const AuthResult.failure(
        errorMessage: 'Unable to login. Please try again.',
      );
    } on TimeoutException catch (_) {
      return const AuthResult.failure(
        errorMessage:
            'Could not reach the server. Please check your connection.',
      );
    } on SocketException catch (_) {
      return const AuthResult.failure(
        errorMessage:
            'Could not reach the server. Please check your connection.',
      );
    } catch (_) {
      return const AuthResult.failure(
        errorMessage: 'Unable to login. Please try again.',
      );
    }
  }

  Future<void> logout(String token) async {
    final uri = _buildUri('/auth/logout');

    try {
      await http.post(
        uri,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );
    } catch (_) {
      // Intentionally swallow logout errors.
    }
  }

  Uri _buildUri(String path) {
    final resolved = _resolveBaseUrl(
      Environment.aiServiceUrl,
    ).replaceAll(RegExp(r'/+$'), '');
    final normalizedPath = path.startsWith('/') ? path : '/$path';
    return Uri.parse('$resolved$normalizedPath');
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
}
