import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AuthStorage {
  static const _tokenKey = 'deepshield_token';
  static const _userIdKey = 'deepshield_user_id';
  static const _emailKey = 'deepshield_email';

  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  Future<void> saveSession(String token, String userId, String email) async {
    await _storage.write(key: _tokenKey, value: token);
    await _storage.write(key: _userIdKey, value: userId);
    await _storage.write(key: _emailKey, value: email);
  }

  Future<Map<String, String?>> loadSession() async {
    final token = await _storage.read(key: _tokenKey);
    final userId = await _storage.read(key: _userIdKey);
    final email = await _storage.read(key: _emailKey);

    if (token == null || userId == null || email == null) {
      return {_tokenKey: null, _userIdKey: null, _emailKey: null};
    }

    return {_tokenKey: token, _userIdKey: userId, _emailKey: email};
  }

  Future<void> clearSession() async {
    await _storage.delete(key: _tokenKey);
    await _storage.delete(key: _userIdKey);
    await _storage.delete(key: _emailKey);
  }
}
