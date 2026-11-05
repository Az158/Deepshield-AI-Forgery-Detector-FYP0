import 'package:flutter_dotenv/flutter_dotenv.dart';

/// -------------------------------
/// ENVIRONMENT CONFIGURATION
/// -------------------------------
/// Load this at app startup in main.dart:
/// ```dart
/// await dotenv.load(fileName: ".env");
/// ```
class Environment {
  /// Base URLs
  static final String apiBaseUrl =
      dotenv.env['API_BASE_URL'] ?? 'https://api.deepshield.com/v1';
  static final String supabaseUrl =
      dotenv.env['SUPABASE_URL'] ?? 'https://your-supabase-url.supabase.co';
  static final String supabaseAnonKey =
      dotenv.env['SUPABASE_ANON_KEY'] ?? 'your-anon-key';

    // AI / Deepfake Detection Service
    static final String aiServiceUrl =
        dotenv.env['DEEPSHIELD_API_URL'] ?? 'http://localhost:8000';
    static final String aiApiKey = dotenv.env['AI_API_KEY'] ?? '';

  /// Blockchain / Polygon Integration
  static final String blockchainRpcUrl =
      dotenv.env['BLOCKCHAIN_RPC_URL'] ?? 'https://polygon-rpc.com';
  static final String smartContractAddress =
      dotenv.env['SMART_CONTRACT_ADDRESS'] ?? '';

  /// Optional Analytics / Monitoring
  static final String sentryDsn = dotenv.env['SENTRY_DSN'] ?? '';
  static final String firebaseApiKey =
      dotenv.env['FIREBASE_API_KEY'] ?? '';

  /// Environment Info
  static final String appEnv = dotenv.env['APP_ENV'] ?? 'development';
  static bool get isProduction => appEnv == 'production';
  static bool get isDevelopment => appEnv == 'development';
}
