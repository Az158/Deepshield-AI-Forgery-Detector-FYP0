# DeepShield Frontend (MVP)

Production-quality Flutter UI for DeepShield, an AI-powered deepfake forgery detector with blockchain verification. This build uses simulated data/services only; networking, AI, and blockchain are placeholders.

## Setup
1) Copy `.env.example` to `.env` and fill values (no real secrets checked in).
2) Install deps: `flutter pub get` (uses `intl`, `google_fonts`, `flutter_svg`, `flutter_dotenv`).
3) Run: `flutter run`.

## Architecture
- `lib/src/config`: theme, constants, environment (.env loaded in `main.dart`).
- `lib/src/data`: models + fake services (auth, bootstrap, analysis, history).
- `lib/src/logic`: app state + simple service locator.
- `lib/src/presentation`: screens, widgets, routes (`Navigator` 1.0).

## Flow
- Splash (3s) → welcome/login/signup (first-launch aware) → home (bottom nav).
- Home: simulate upload/link input → analysis progress screen → result → report/blockchain sheet.
- History: in-memory list from fake analyses.
- Settings/About: fake profile data, logout back to auth flow.

## Notes
- No real API calls or storage; all data is in-memory placeholders for wiring UI/UX.
- Poppins typography applied via `google_fonts`.
