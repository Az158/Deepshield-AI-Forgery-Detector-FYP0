import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_svg/flutter_svg.dart';

import 'package:deepshield/src/core/theme.dart';
import 'package:deepshield/src/core/constants.dart';
import 'package:deepshield/src/core/utils/service_locator.dart';
import 'package:deepshield/src/routes/app_router.dart';

/// Splash screen with simple animation then navigation to auth/home.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fadeIn;
  late Animation<double> _scaleIn;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    );

    _fadeIn = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeInOutCubic,
    );
    _scaleIn = Tween<double>(
      begin: 0.9,
      end: 1.0,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutBack));

    _controller.forward();
    _kickoffNavigation();
  }

  Future<void> _kickoffNavigation() async {
    await Future.delayed(const Duration(seconds: 3));
    await ServiceLocator.authProvider.tryAutoLogin();
    final isLoggedIn = ServiceLocator.authProvider.isLoggedIn;

    if (!mounted) return;

    if (isLoggedIn) {
      Navigator.pushReplacementNamed(context, AppRoutes.home);
    } else {
      Navigator.pushReplacementNamed(context, AppRoutes.login);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: [
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color(0xFF0E2546), Color(0xFF060B14)],
              ),
            ),
          ),
          Positioned.fill(child: _buildSplashBackground()),
          SafeArea(
            child: FadeTransition(
              opacity: _fadeIn,
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    AnimatedBuilder(
                      animation: _controller,
                      builder: (context, child) {
                        return AnimatedScale(
                          scale: _scaleIn.value,
                          duration: const Duration(milliseconds: 1200),
                          curve: Curves.easeOutBack,
                          child: child,
                        );
                      },
                      child: Image.asset(
                        'assets/images/logo.png',
                        height: size.height * 0.28,
                        width: size.height * 0.28,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    Text(
                      'DeepShield',
                      style: GoogleFonts.pacifico(
                        fontSize: 55,
                        color: AppColors.primary,
                        fontWeight: FontWeight.w300,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: AppSpacing.lg),
                    Text(
                      'Securing Tomorrow,\nToday',
                      style: GoogleFonts.pacifico(
                        fontSize: 30,
                        fontStyle: FontStyle.italic,
                        color: AppColors.secondary.withOpacity(0.9),
                        height: 1.4,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSplashBackground() {
    const assetPath = 'assets/vectors/splash_bg.svg';
    if (assetPath.isNotEmpty) {
      return SvgPicture.asset(assetPath, fit: BoxFit.cover);
    }

    return Container(color: const Color(0xFF060B14));
  }
}
