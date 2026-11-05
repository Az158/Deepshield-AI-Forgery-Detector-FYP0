import 'package:flutter/material.dart';

import '../../../core/constants.dart';
import '../../../core/theme.dart';
import '../../../core/utils/service_locator.dart';
import '../../widgets/loading_overlay.dart';
import '../../widgets/primary_button.dart';
import '../../../routes/app_router.dart';

/// Login UI with fake auth validation.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _handledRouteMessage = false;
  bool _obscurePassword = true;

  @override
  void initState() {
    super.initState();
    _emailCtrl.addListener(_clearAuthError);
    _passwordCtrl.addListener(_clearAuthError);
  }

  void _clearAuthError() {
    ServiceLocator.authProvider.clearError();
  }

  @override
  void dispose() {
    _emailCtrl.removeListener(_clearAuthError);
    _passwordCtrl.removeListener(_clearAuthError);
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;
    final authProvider = ServiceLocator.authProvider;
    await authProvider.login(_emailCtrl.text.trim(), _passwordCtrl.text);

    if (!mounted) return;
    if (authProvider.isLoggedIn) {
      Navigator.pushNamedAndRemoveUntil(
        context,
        AppRoutes.home,
        (route) => false,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_handledRouteMessage) {
      _handledRouteMessage = true;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        final args = ModalRoute.of(context)?.settings.arguments;
        if (!mounted || args is! String || args.trim().isEmpty) {
          return;
        }
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(args)));
      });
    }

    return ListenableBuilder(
      listenable: ServiceLocator.authProvider,
      builder: (context, _) {
        final authProvider = ServiceLocator.authProvider;
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
                                'Welcome Back',
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
                                  if (value.length < 6) {
                                    return 'Password is too short';
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: AppSpacing.xl),
                              if (authProvider.errorMessage != null)
                                Padding(
                                  padding: const EdgeInsets.only(
                                    bottom: AppSpacing.md,
                                  ),
                                  child: Text(
                                    authProvider.errorMessage!,
                                    style: Theme.of(context).textTheme.bodySmall
                                        ?.copyWith(color: Colors.redAccent),
                                  ),
                                ),
                              PrimaryButton(
                                label: 'Login',
                                onPressed: authProvider.isLoading
                                    ? null
                                    : _handleLogin,
                                isBusy: authProvider.isLoading,
                              ),
                              const SizedBox(height: AppSpacing.md),
                              Align(
                                alignment: Alignment.center,
                                child: TextButton(
                                  onPressed: () {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text(
                                          'Password reset is not available yet. Contact support if you need help.',
                                        ),
                                      ),
                                    );
                                  },
                                  child: const Text('Forgot password?'),
                                ),
                              ),
                              const SizedBox(height: AppSpacing.sm),
                              Align(
                                alignment: Alignment.center,
                                child: TextButton(
                                  onPressed: () => Navigator.pushNamed(
                                    context,
                                    AppRoutes.signup,
                                  ),
                                  child: Text(
                                    "Don't have an account? Sign Up",
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
