import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'package:deepshield/src/core/theme.dart';
import 'package:deepshield/src/core/utils/service_locator.dart';
import 'package:deepshield/src/presentation/screens/auth/login_screen.dart';
import 'package:deepshield/src/presentation/screens/home/home_shell.dart';
import 'package:deepshield/src/routes/app_router.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: '.env');
  runApp(const DeepShieldApp());
}

class DeepShieldApp extends StatefulWidget {
  const DeepShieldApp({super.key});

  @override
  State<DeepShieldApp> createState() => _DeepShieldAppState();
}

class _DeepShieldAppState extends State<DeepShieldApp> {
  late final Future<void> _autoLoginFuture;

  @override
  void initState() {
    super.initState();
    _autoLoginFuture = ServiceLocator.authProvider.tryAutoLogin();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<void>(
      future: _autoLoginFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return MaterialApp(
            title: 'DeepShield',
            debugShowCheckedModeBanner: false,
            theme: AppTheme.darkTheme,
            home: const Scaffold(
              backgroundColor: AppColors.background,
              body: Center(child: CircularProgressIndicator()),
            ),
          );
        }

        return MaterialApp(
          title: 'DeepShield',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.darkTheme,
          onGenerateRoute: AppRouter.onGenerateRoute,
          home: ServiceLocator.authProvider.isLoggedIn
              ? const HomeShell()
              : const LoginScreen(),
        );
      },
    );
  }
}
