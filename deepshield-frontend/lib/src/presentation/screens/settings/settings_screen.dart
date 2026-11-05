import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../core/constants.dart';
import '../../../core/theme.dart';
import '../../../core/utils/service_locator.dart';
import '../../../data/models/health_status.dart';
import '../../../routes/app_router.dart';
import '../../widgets/primary_button.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  HealthStatus? _healthStatus;
  bool _isLoadingHealth = false;

  @override
  void initState() {
    super.initState();
    _fetchHealth();
  }

  Future<void> _fetchHealth() async {
    setState(() => _isLoadingHealth = true);
    try {
      final status = await ServiceLocator.deepfakeService.checkHealth();
      if (!mounted) return;
      setState(() {
        _healthStatus = status;
        _isLoadingHealth = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _healthStatus = null;
        _isLoadingHealth = false;
      });
    }
  }

  Future<void> _logout() async {
    final shouldLogout = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Log out?'),
        content: const Text('You will need to sign in again to run analyses.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Log out'),
          ),
        ],
      ),
    );

    if (shouldLogout != true) return;

    await ServiceLocator.authProvider.logout();
    if (!mounted) return;
    Navigator.pushNamedAndRemoveUntil(
      context,
      AppRoutes.login,
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = ServiceLocator.authProvider;

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: SingleChildScrollView(
        padding: AppSpacing.screenPadding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _SectionHeader(
              title: 'Account',
              subtitle: 'Signed-in user for protected analysis requests.',
            ),
            const SizedBox(height: AppSpacing.sm),
            _SurfaceCard(
              child: Row(
                children: [
                  const CircleAvatar(
                    radius: 28,
                    backgroundImage: AssetImage('assets/images/logo.png'),
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          authProvider.userDisplayName,
                          style: Theme.of(context).textTheme.titleMedium,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          (authProvider.userEmail ?? '').isNotEmpty
                              ? authProvider.userEmail!
                              : 'user@deepshield.app',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: AppColors.textSecondary,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            _SectionHeader(
              title: 'System Status',
              subtitle: 'Backend availability controls upload and report flows.',
            ),
            const SizedBox(height: AppSpacing.sm),
            _buildHealthCard(),
            const SizedBox(height: AppSpacing.lg),
            _SectionHeader(
              title: 'About',
              subtitle: 'DeepShield analyzes media and reports confidence, evidence, and verification status.',
            ),
            const SizedBox(height: AppSpacing.sm),
            _SurfaceCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Use results as decision support. Report and blockchain availability depend on the backend response.',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    'Open the About tab for a fuller explanation of results, limitations, and verification.',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            PrimaryButton(
              label: 'Log out',
              onPressed: _logout,
              icon: const Icon(Icons.logout_rounded),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHealthCard() {
    return _SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (_isLoadingHealth)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (_healthStatus == null)
            _StatusRow(
              icon: Icons.error_outline,
              color: Colors.redAccent,
              title: 'Backend unreachable',
              subtitle: 'Check that the API is running, then retry.',
              actionLabel: 'Retry',
              onAction: _fetchHealth,
            )
          else ...[
            _StatusRow(
              icon: Icons.check_circle_outline,
              color: Colors.green,
              title: 'Backend connected',
              subtitle: 'Status: ${_healthStatus!.status}',
              actionLabel: 'Re-check',
              onAction: _fetchHealth,
            ),
            const SizedBox(height: AppSpacing.md),
            _metaRow(
              'Primary model',
              _modelStatus(
                reported: _healthStatus!.ucfReported,
                loaded: _healthStatus!.ucfLoaded,
              ),
            ),
            _metaRow(
              'Xception Model',
              _modelStatus(
                reported: _healthStatus!.xceptionReported,
                loaded: _healthStatus!.xceptionLoaded,
              ),
            ),
            _metaRow('AI Service', _healthStatus!.aiService),
            _metaRow(
              'Last Checked',
              _healthStatus!.lastChecked == null
                  ? 'Unknown'
                  : DateFormat('h:mm:ss a').format(_healthStatus!.lastChecked!),
            ),
          ],
        ],
      ),
    );
  }

  String _modelStatus({required bool reported, required bool loaded}) {
    if (!reported) {
      return 'Not reported';
    }
    return loaded ? 'Loaded' : 'Not loaded';
  }

  Widget _metaRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: AppColors.textSecondary),
            ),
          ),
          Expanded(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: const TextStyle(fontWeight: FontWeight.w600),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          subtitle,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }
}

class _SurfaceCard extends StatelessWidget {
  const _SurfaceCard({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.cardOverlay,
        borderRadius: AppRadii.card,
        border: Border.all(color: AppColors.border),
        boxShadow: const [AppShadows.soft],
      ),
      child: child,
    );
  }
}

class _StatusRow extends StatelessWidget {
  const _StatusRow({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    required this.actionLabel,
    required this.onAction,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final String actionLabel;
  final VoidCallback onAction;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: color),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
        TextButton(
          onPressed: onAction,
          child: Text(actionLabel),
        ),
      ],
    );
  }
}
