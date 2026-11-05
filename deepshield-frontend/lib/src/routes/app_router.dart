import 'package:flutter/material.dart';

import '../core/utils/service_locator.dart';
import '../data/models/analysis_result.dart';
import '../data/models/media_item.dart';
import '../data/models/report_summary.dart';
import '../data/models/deepfake_request.dart';
import '../presentation/screens/analysis/analysis_progress_screen.dart';
import '../presentation/screens/auth/login_screen.dart';
import '../presentation/screens/auth/signup_screen.dart';
import '../presentation/screens/auth/welcome_screen.dart';
import '../presentation/screens/home/home_shell.dart';
import '../presentation/screens/report/report_screen.dart';
import '../presentation/screens/result/result_screen.dart';
import '../presentation/screens/splash/splash_screen.dart';

class AppRoutes {
  static const splash = '/splash';
  static const welcome = '/welcome';
  static const login = '/login';
  static const signup = '/signup';
  static const home = '/home';
  static const analysisProgress = '/analysis-progress';
  static const result = '/result';
  static const report = '/report';
}

class AppRouter {
  static Route<dynamic> onGenerateRoute(RouteSettings settings) {
    final isLoggedIn = ServiceLocator.authProvider.isLoggedIn;

    switch (settings.name) {
      case AppRoutes.splash:
        return MaterialPageRoute(builder: (_) => const SplashScreen());
      case AppRoutes.welcome:
        return MaterialPageRoute(builder: (_) => const WelcomeScreen());
      case AppRoutes.login:
        return MaterialPageRoute(
          settings: settings,
          builder: (_) => const LoginScreen(),
        );
      case AppRoutes.signup:
        return MaterialPageRoute(builder: (_) => const SignUpScreen());
      case AppRoutes.home:
        if (!isLoggedIn) {
          return MaterialPageRoute(builder: (_) => const LoginScreen());
        }
        return MaterialPageRoute(builder: (_) => const HomeShell());
      case AppRoutes.analysisProgress:
        if (!isLoggedIn) {
          return MaterialPageRoute(builder: (_) => const LoginScreen());
        }
        final argument = settings.arguments;
        if (argument is! DeepfakeRequest) {
          return _errorRoute(
            'Select a media file before starting analysis.',
          );
        }
        return MaterialPageRoute(
          builder: (_) => AnalysisProgressScreen(request: argument),
        );
      case AppRoutes.result:
        if (!isLoggedIn) {
          return MaterialPageRoute(builder: (_) => const LoginScreen());
        }
        final dynamic argument = settings.arguments;
        final AnalysisResult result;
        if (argument is AnalysisResult) {
          result = argument;
        } else if (argument is Map<String, dynamic>) {
          final media = MediaItem(
            id:
                argument['analysis_id']?.toString() ??
                argument['id']?.toString() ??
                '',
            title: argument['filename']?.toString() ?? 'Unknown file',
            url: argument['media_url']?.toString() ?? '',
            type:
                argument['type']?.toString() ??
                argument['media_type']?.toString() ??
                'image',
            thumbnailAsset: 'assets/images/logo.png',
          );
          result = AnalysisResult.fromJson(argument, media);
        } else {
          return _errorRoute(
            'Result data is unavailable. Return to history and reopen the analysis.',
          );
        }
        return MaterialPageRoute(builder: (_) => ResultScreen(result: result));
      case AppRoutes.report:
        if (!isLoggedIn) {
          return MaterialPageRoute(builder: (_) => const LoginScreen());
        }
        final argument = settings.arguments;
        if (argument is! ReportSummary) {
          return _errorRoute('Report data is unavailable.');
        }
        return MaterialPageRoute(
          builder: (_) => ReportScreen(summary: argument),
        );
      default:
        return _errorRoute('Route not found.');
    }
  }

  static Route<dynamic> _errorRoute(String message) {
    return MaterialPageRoute(
      builder: (_) => Scaffold(
        appBar: AppBar(title: const Text('DeepShield')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(message, textAlign: TextAlign.center),
          ),
        ),
      ),
    );
  }
}
