import 'package:flutter/material.dart';

import '../../../core/theme.dart';
import '../../../core/utils/service_locator.dart';
import '../../../routes/app_router.dart';
import '../history/history_screen.dart';
import '../settings/settings_screen.dart';
import '../about/about_screen.dart';
import 'home_tab.dart';

/// Shell with bottom navigation hosting main sections.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  @override
  void initState() {
    super.initState();
    ServiceLocator.authProvider.addListener(_onAuthChanged);
  }

  @override
  void dispose() {
    ServiceLocator.authProvider.removeListener(_onAuthChanged);
    super.dispose();
  }

  void _onAuthChanged() {
    if (!mounted) {
      return;
    }
    if (ServiceLocator.authProvider.isLoggedIn) {
      return;
    }

    Navigator.pushNamedAndRemoveUntil(
      context,
      AppRoutes.login,
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _buildTab(_index),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _index,
        onTap: (value) => setState(() => _index = value),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.home_outlined),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.history_rounded),
            label: 'History',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.settings_outlined),
            label: 'Settings',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.info_outline),
            label: 'About',
          ),
        ],
        backgroundColor: AppColors.background,
      ),
    );
  }

  Widget _buildTab(int index) {
    switch (index) {
      case 0:
        return const HomeTab();
      case 1:
        return const HistoryScreen();
      case 2:
        return const SettingsScreen();
      case 3:
        return const AboutScreen();
      default:
        return const HomeTab();
    }
  }
}
