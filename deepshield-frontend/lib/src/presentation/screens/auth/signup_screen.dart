import 'package:flutter/material.dart';

import '../../../core/constants.dart';
import '../../../core/theme.dart';
import '../../../core/utils/service_locator.dart';
import '../../widgets/loading_overlay.dart';
import '../../widgets/primary_button.dart';

/// Sign up UI with fake auth creation.
class SignUpScreen extends StatefulWidget {
  const SignUpScreen({super.key});

  @override
  State<SignUpScreen> createState() => _SignUpScreenState();
}

class _SignUpScreenState extends State<SignUpScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  String? _localErrorMessage;
  bool _obscurePassword = true;
  bool _obscureConfirm = true;

  @override
  void initState() {
    super.initState();
    _emailCtrl.addListener(_clearAuthError);
    _passwordCtrl.addListener(_clearAuthError);
    _confirmCtrl.addListener(_clearAuthError);
  }

  void _clearAuthError() {
    ServiceLocator.authProvider.clearError();
    if (_localErrorMessage != null) {
      setState(() => _localErrorMessage = null);
    }
  }

  @override
  void dispose() {
    _emailCtrl.removeListener(_clearAuthError);
    _passwordCtrl.removeListener(_clearAuthError);
    _confirmCtrl.removeListener(_clearAuthError);
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    _confirmCtrl.dispose();
    super.dispose();
  }

  Future<void> _handleSignup() async {
    if (!_formKey.currentState!.validate()) return;
    if (_passwordCtrl.text != _confirmCtrl.text) {
      setState(() {
        _localErrorMessage = 'Passwords do not match';
      });
      return;
    }

    final authProvider = ServiceLocator.authProvider;
    await authProvider.signup(_emailCtrl.text.trim(), _passwordCtrl.text);

    if (!mounted) return;
    if (authProvider.signupSuccessMessage != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(authProvider.signupSuccessMessage!)),
      );
      authProvider.clearSignupSuccessMessage();
      Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: ServiceLocator.authProvider,
      builder: (context, _) {
        final authProvider = ServiceLocator.authProvider;
        final errorMessage = _localErrorMessage ?? authProvider.errorMessage;

        return Scaffold(
          body: LoadingOverlay(
            visible: authProvider.isLoading,
            child: Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Color(0xFF0E2546), Color(0xFF070C15)],
                ),
              ),
              child: SafeArea(
                child: SingleChildScrollView(
                  padding: AppSpacing.screenPadding,
                  child: Column(
                    children: [
                      const SizedBox(height: AppSpacing.xl),
                      Image.asset('assets/images/logo.png', height: 90),
                      const SizedBox(height: AppSpacing.md),
                      Text(
                        'Unmasking AI-generated deception',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: AppSpacing.xl),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.lg,
                          vertical: AppSpacing.xl,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.cardOverlay,
                          borderRadius: AppRadii.card,
                          boxShadow: const [AppShadows.medium],
                          border: Border.all(color: AppColors.subtle),
                        ),
                        child: Form(
                          key: _formKey,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Create Account',
                                style: Theme.of(context).textTheme.headlineSmall
                                    ?.copyWith(fontWeight: FontWeight.w700),
                              ),
                              const SizedBox(height: AppSpacing.lg),
                              TextFormField(
                                controller: _emailCtrl,
                                keyboardType: TextInputType.emailAddress,
                                decoration: const InputDecoration(
                                  prefixIcon: Icon(Icons.mail_outline),
                                  hintText: 'Email Address',
                                ),
                                validator: (value) {
                                  final email = value?.trim() ?? '';
                                  if (email.isEmpty) {
                                    return 'Email is required';
                                  }
                                  final validEmail = RegExp(
                                    r'^[^@\s]+@[^@\s]+\.[^@\s]+$',
                                  ).hasMatch(email);
                                  if (!validEmail) {
                                    return 'Enter a valid email';
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: AppSpacing.md),
                              TextFormField(
                                controller: _passwordCtrl,
                                obscureText: _obscurePassword,
                                decoration: const InputDecoration(
                                  prefixIcon: Icon(Icons.lock_outline),
                                  hintText: 'Password',
                                ).copyWith(
                                  suffixIcon: IconButton(
                                    tooltip: _obscurePassword
                                        ? 'Show password'
                                        : 'Hide password',
                                    onPressed: () => setState(
                                      () => _obscurePassword = !_obscurePassword,
                                    ),
                                    icon: Icon(
                                      _obscurePassword
                                          ? Icons.visibility_outlined
                                          : Icons.visibility_off_outlined,
                                    ),
                                  ),
                                ),
                                validator: (value) {
                                  if (value == null || value.isEmpty) {
                                    return 'Password is required';
                                  }
                                  if (value.length < 8) {
                                    return 'Use at least 8 characters';
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: AppSpacing.md),
                              TextFormField(
                                controller: _confirmCtrl,
                                obscureText: _obscureConfirm,
                                decoration: const InputDecoration(
                                  prefixIcon: Icon(Icons.lock_outline),
                                  hintText: 'Confirm Password',
                                ).copyWith(
                                  suffixIcon: IconButton(
                                    tooltip: _obscureConfirm
                                        ? 'Show password'
                                        : 'Hide password',
                                    onPressed: () => setState(
                                      () => _obscureConfirm = !_obscureConfirm,
                                    ),
                                    icon: Icon(
                                      _obscureConfirm
                                          ? Icons.visibility_outlined
                                          : Icons.visibility_off_outlined,
                                    ),
                                  ),
                                ),
                                validator: (value) {
                                  if (value == null || value.isEmpty) {
                                    return 'Confirm your password';
                                  }
                                  if (value != _passwordCtrl.text) {
                                    return 'Passwords do not match';
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: AppSpacing.xl),
                              if (errorMessage != null)
                                Padding(
                                  padding: const EdgeInsets.only(
                                    bottom: AppSpacing.md,
                                  ),
                                  child: Text(
                                    errorMessage,
                                    style: Theme.of(context).textTheme.bodySmall
                                        ?.copyWith(color: Colors.redAccent),
                                  ),
                                ),
                              PrimaryButton(
                                label: 'Sign Up',
                                onPressed: authProvider.isLoading
                                    ? null
                                    : _handleSignup,
                                isBusy: authProvider.isLoading,
                              ),
                              const SizedBox(height: AppSpacing.md),
                              Align(
                                alignment: Alignment.center,
                                child: TextButton(
                                  onPressed: () => Navigator.pop(context),
                                  child: Text(
                                    'Already have an account? Login',
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodyMedium
                                        ?.copyWith(
                                          color: AppColors.primary,
                                          fontWeight: FontWeight.w600,
                                        ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}
