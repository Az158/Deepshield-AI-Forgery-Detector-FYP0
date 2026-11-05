import 'package:flutter/material.dart';

import '../../core/theme.dart';

class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    super.key,
    required this.label,
    this.onPressed,
    this.icon,
    this.isBusy = false,
    this.fullWidth = true,
  });

  final String label;
  final VoidCallback? onPressed;
  final Widget? icon;
  final bool isBusy;
  final bool fullWidth;

  @override
  Widget build(BuildContext context) {
    final effectiveOnPressed = isBusy ? null : onPressed;

    return SizedBox(
      width: fullWidth ? double.infinity : null,
      height: 48,
      child: _AnimatedPress(
        enabled: effectiveOnPressed != null,
        child: ElevatedButton(
          onPressed: effectiveOnPressed,
          style: ElevatedButton.styleFrom(
            elevation: 6,
            shadowColor: AppColors.primary.withOpacity(0.35),
            padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 18),
          ),
          child: isBusy
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.5,
                    color: Colors.white,
                  ),
                )
              : FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (icon != null) ...[
                        IconTheme(
                          data: const IconThemeData(
                            size: 20,
                            color: Colors.white,
                          ),
                          child: icon!,
                        ),
                        const SizedBox(width: 8),
                      ],
                      Text(
                        label,
                        style: Theme.of(context)
                            .textTheme
                            .labelLarge
                            ?.copyWith(color: Colors.white),
                        overflow: TextOverflow.ellipsis,
                        maxLines: 1,
                      ),
                    ],
                  ),
                ),
        ),
      ),
    );
  }
}

class _AnimatedPress extends StatefulWidget {
  const _AnimatedPress({required this.child, required this.enabled});
  final Widget child;
  final bool enabled;

  @override
  State<_AnimatedPress> createState() => _AnimatedPressState();
}

class _AnimatedPressState extends State<_AnimatedPress> {
  double _scale = 1.0;

  void _animate(bool down) {
    if (!widget.enabled) return;
    setState(() {
      _scale = down ? 0.97 : 1.0;
    });
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: widget.enabled ? (_) => _animate(true) : null,
      onTapUp: widget.enabled ? (_) => _animate(false) : null,
      onTapCancel: widget.enabled ? () => _animate(false) : null,
      child: AnimatedScale(
        scale: _scale,
        duration: const Duration(milliseconds: 120),
        curve: Curves.easeOut,
        child: widget.child,
      ),
    );
  }
}
