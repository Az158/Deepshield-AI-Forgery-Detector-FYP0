import 'package:flutter/material.dart';

import '../../../core/constants.dart';
import '../../../core/theme.dart';
import '../../../routes/app_router.dart';
import '../../widgets/primary_button.dart';

/// First-time welcome screen with branding and CTA into auth.
class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF0E2546), Color(0xFF070C15)],
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: AppSpacing.screenPadding,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Spacer(),
                Image.asset('assets/images/logo.png', height: 120),
                const SizedBox(height: AppSpacing.lg),
                Text(
                  'Unmasking AI-generated deception',
                  style: Theme.of(context)
                      .textTheme
                      .headlineSmall
                      ?.copyWith(color: Colors.white),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.xl),
                PrimaryButton(
                  label: 'Login',
                  onPressed: () =>
                      Navigator.pushReplacementNamed(context, AppRoutes.login),
                ),
                const SizedBox(height: AppSpacing.md),
                PrimaryButton(
                  label: 'Create account',
                  onPressed: () =>
                      Navigator.pushReplacementNamed(context, AppRoutes.signup),
                  icon: const Icon(Icons.person_add_alt_1_rounded),
                ),
                const Spacer(),
                Text(
                  'DeepShield - Securing Tomorrow, Today',
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: AppColors.textSecondary),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
