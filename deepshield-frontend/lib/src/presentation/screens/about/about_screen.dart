import 'package:flutter/material.dart';

import '../../../core/constants.dart';
import '../../../core/theme.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('About')),
      body: SingleChildScrollView(
        padding: AppSpacing.screenPadding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'DeepShield',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: AppSpacing.xs),
            Text(
              'AI-assisted media verification with forensic reports and optional blockchain anchoring.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            _InfoCard(
              title: 'What it does',
              icon: Icons.shield_outlined,
              children: const [
                'Checks uploaded images or videos for signs of AI generation or manipulation.',
                'Shows a confidence score and a plain-language interpretation.',
                'Creates a report when the backend returns one.',
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            _InfoCard(
              title: 'How it works',
              icon: Icons.route_outlined,
              children: const [
                '1. Upload a supported media file.',
                '2. The backend runs AI analysis.',
                '3. DeepShield shows the result and available evidence.',
                '4. Reports may be anchored on-chain for later verification.',
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            _InfoCard(
              title: 'What results mean',
              icon: Icons.analytics_outlined,
              children: const [
                'High confidence means the model found a strong signal.',
                'Medium confidence should be reviewed with context.',
                'Low confidence is best treated as inconclusive.',
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            _InfoCard(
              title: 'Limitations',
              icon: Icons.info_outline,
              children: const [
                'No AI detector is perfect. Use results as decision support, not final proof.',
                'Poor quality, compressed, or edited files can reduce reliability.',
                'Report and blockchain status depend on backend availability.',
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            _InfoCard(
              title: 'Support',
              icon: Icons.mail_outline,
              children: const ['support@deepshield.app'],
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({
    required this.title,
    required this.icon,
    required this.children,
  });

  final String title;
  final IconData icon;
  final List<String> children;

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
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: AppColors.primary, size: 20),
              const SizedBox(width: AppSpacing.sm),
              Text(
                title,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          ...children.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.xs),
              child: Text(
                item,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
