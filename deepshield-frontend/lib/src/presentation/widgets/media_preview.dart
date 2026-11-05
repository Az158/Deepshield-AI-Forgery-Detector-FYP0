import 'package:flutter/material.dart';

import '../../core/constants.dart';
import '../../core/theme.dart';

class MediaPreview extends StatelessWidget {
  const MediaPreview({
    super.key,
    this.thumbnailAsset,
    this.title,
    this.subtitle,
    this.compact = false,
  });

  final String? thumbnailAsset;
  final String? title;
  final String? subtitle;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    if (compact || (title == null && subtitle == null)) {
      return _squareThumb();
    }

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: AppRadii.card,
        border: Border.all(color: AppColors.border),
        boxShadow: const [AppShadows.soft],
      ),
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Row(
        children: [
          _squareThumb(),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (title != null)
                  Text(
                    title!,
                    style: Theme.of(context)
                        .textTheme
                        .titleSmall
                        ?.copyWith(fontWeight: FontWeight.w700),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                if (subtitle != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    subtitle!,
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: AppColors.textSecondary),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          )
        ],
      ),
    );
  }

  Widget _squareThumb() {
    return ClipRRect(
      borderRadius: AppRadii.card,
      child: Container(
        width: 72,
        height: 72,
        color: AppColors.border.withOpacity(0.2),
        child: thumbnailAsset != null
            ? Image.asset(thumbnailAsset!, fit: BoxFit.cover)
            : _ShimmerPlaceholder(),
      ),
    );
  }
}

class _ShimmerPlaceholder extends StatefulWidget {
  @override
  State<_ShimmerPlaceholder> createState() => _ShimmerPlaceholderState();
}

class _ShimmerPlaceholderState extends State<_ShimmerPlaceholder>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    duration: const Duration(milliseconds: 1200),
    vsync: this,
  )..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                AppColors.border.withOpacity(0.15),
                AppColors.border.withOpacity(0.35),
                AppColors.border.withOpacity(0.15),
              ],
              stops: [
                (_controller.value - 0.3).clamp(0.0, 1.0),
                _controller.value,
                (_controller.value + 0.3).clamp(0.0, 1.0),
              ],
            ),
          ),
        );
      },
    );
  }
}
