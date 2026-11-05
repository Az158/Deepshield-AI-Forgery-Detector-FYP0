class AuthResult {
  const AuthResult.success({
    required this.accessToken,
    required this.userId,
    required this.email,
  }) : success = true,
       errorMessage = null;

  const AuthResult.failure({required this.errorMessage})
    : success = false,
      accessToken = null,
      userId = null,
      email = null;

  final bool success;
  final String? accessToken;
  final String? userId;
  final String? email;
  final String? errorMessage;
}
