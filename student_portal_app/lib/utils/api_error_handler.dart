import 'package:flutter/material.dart';

/// Utility class for handling API errors and displaying user-friendly messages
class ApiErrorHandler {
  /// Extract a user-friendly error message from API response
  static String getErrorMessage(Map<String, dynamic> response) {
    if (response['isHtmlResponse'] == true) {
      return _getHtmlErrorSuggestion(response['statusCode']);
    }
    if (response['parseError'] != null) {
      return 'Server returned invalid data. Please try again later.';
    }
    if (response['message']?.toString().contains('Unexpected content type') == true) {
      return 'Server returned unexpected data format. Please try again later.';
    }
    if (response['message'] != null && response['message'].toString().isNotEmpty) {
      return response['message'].toString();
    }
    return 'An unexpected error occurred. Please try again.';
  }
  
  /// Get a helpful suggestion based on HTTP status code for HTML errors
  static String _getHtmlErrorSuggestion(int? statusCode) {
    switch (statusCode) {
      case 404: return 'The requested endpoint was not found (404).';
      case 403: return 'Access forbidden (403).';
      case 401: return 'Authentication required (401). Please log in again.';
      case 500: return 'Internal server error (500). Please try again later.';
      case 502: return 'Bad gateway (502). Server communication issue.';
      case 503: return 'Service unavailable (503). Server may be down.';
      case 504: return 'Gateway timeout (504). Server took too long.';
      default: return 'Server returned HTML page (Status $statusCode).';
    }
  }
  
  /// Show a snackbar with the error message
  static void showSnackbar(BuildContext context, Map<String, dynamic> response) {
    final message = getErrorMessage(response);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red[700],
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 4),
        action: SnackBarAction(
          label: 'Dismiss',
          textColor: Colors.white,
          onPressed: () {},
        ),
      ),
    );
  }
  
  /// Show a detailed error dialog (useful for development or when user needs more info)
  static void showErrorDialog(BuildContext context, Map<String, dynamic> response) {
    final message = getErrorMessage(response);
    final statusCode = response['statusCode'];
    final rawBody = response['rawBody'];
    
    showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Error'),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(message, style: const TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 16),
                if (statusCode != null)
                  Text('Status Code: $statusCode',
                    style: TextStyle(color: Colors.red[700], fontWeight: FontWeight.w500)),
                if (rawBody != null && rawBody.toString().isNotEmpty) ...[
                  const SizedBox(height: 12),
                  const Text('Raw Response (first 200 chars):',
                    style: TextStyle(fontWeight: FontWeight.w500)),
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.grey[200],
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      rawBody.toString().length > 200 
                        ? '${rawBody.toString().substring(0, 200)}...' 
                        : rawBody.toString(),
                      style: const TextStyle(fontSize: 12, fontFamily: 'monospace'),
                    ),
                  ),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('OK'),
            ),
          ],
        );
      },
    );
  }
  
  /// Log detailed error information for debugging
  static void logError(Map<String, dynamic> response, [String? additionalContext]) {
    debugPrint('═══════════════════════════════════════════');
    debugPrint('API ERROR DETAILS');
    if (additionalContext != null) debugPrint('Context: $additionalContext');
    debugPrint('Status Code: ${response['statusCode']}');
    debugPrint('Message: ${response['message']}');
    debugPrint('Is HTML Response: ${response['isHtmlResponse']}');
    debugPrint('Parse Error: ${response['parseError']}');
    if (response['rawBody'] != null) {
      debugPrint('Raw Body (first 500 chars):');
      debugPrint(response['rawBody'].toString().length > 500 
        ? '${response['rawBody'].toString().substring(0, 500)}...' 
        : response['rawBody'].toString());
    }
    debugPrint('═══════════════════════════════════════════');
  }
}