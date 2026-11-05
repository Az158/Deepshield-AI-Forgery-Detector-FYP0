/// Fake auth service for MVP only. No real networking or persistence.
class AuthService {
  bool _isLoggedIn = false;
  String _email = '';
  String _name = 'DeepShield User';

  bool get isLoggedIn => _isLoggedIn;
  String get email => _email;
  String get name => _name;

  Future<bool> login({required String email, required String password}) async {
    await Future.delayed(const Duration(milliseconds: 500));
    _email = email;
    _name = 'DeepShield User';
    _isLoggedIn = true;
    return _isLoggedIn;
  }

  Future<bool> signUp({
    required String name,
    required String email,
    required String password,
  }) async {
    await Future.delayed(const Duration(milliseconds: 700));
    _name = name;
    _email = email;
    _isLoggedIn = true;
    return _isLoggedIn;
  }

  Future<void> logout() async {
    _isLoggedIn = false;
    _email = '';
    _name = 'DeepShield User';
  }
}
