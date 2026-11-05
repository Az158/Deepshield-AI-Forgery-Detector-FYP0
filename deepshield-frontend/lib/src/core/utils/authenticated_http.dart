import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../routes/app_router.dart';
import 'service_locator.dart';

Future<void> handleUnauthorized(BuildContext context) async {
  await ServiceLocator.authProvider.logout();
  if (!context.mounted) {
    return;
  }

  Navigator.of(context).pushNamedAndRemoveUntil(
    AppRoutes.login,
    (route) => false,
    arguments: 'Your session has expired. Please log in again.',
  );
}

Future<http.Response> authenticatedGet(
  String url,
  String token,
  BuildContext context, {
  Duration timeout = const Duration(seconds: 15),
}) async {
  debugPrint('[authenticatedGet] GET $url tokenPresent=${token.isNotEmpty}');
  final response = await http
      .get(Uri.parse(url), headers: {'Authorization': 'Bearer $token'})
      .timeout(timeout);
  debugPrint(
    '[authenticatedGet] status=${response.statusCode} body=${_clipBody(response.body)}',
  );

  if (response.statusCode == 401) {
    await handleUnauthorized(context);
    throw Exception('Session expired');
  }

  return response;
}

Future<http.Response> authenticatedPost(
  String url,
  String token,
  dynamic body,
  BuildContext context, {
  Duration timeout = const Duration(seconds: 60),
}) async {
  final response = await http
      .post(
        Uri.parse(url),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: jsonEncode(body),
      )
      .timeout(timeout);

  if (response.statusCode == 401) {
    await handleUnauthorized(context);
    throw Exception('Session expired');
  }

  return response;
}

String _clipBody(String value, {int max = 240}) {
  if (value.length <= max) {
    return value;
  }
  return '${value.substring(0, max)}...';
}
