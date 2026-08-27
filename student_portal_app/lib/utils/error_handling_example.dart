// EXAMPLE: How to use the robust error handling in your controllers
// This file demonstrates best practices for handling API errors gracefully

import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'api_error_handler.dart';

class ErrorHandlingExample extends StatefulWidget {
  const ErrorHandlingExample({Key? key}) : super(key: key);

  @override
  State<ErrorHandlingExample> createState() => _ErrorHandlingExampleState();
}

class _ErrorHandlingExampleState extends State<ErrorHandlingExample> {
  final ApiService _apiService = ApiService();
  bool _isLoading = false;
  String? _errorMessage;
  Map<String, dynamic>? _lastResponse;

  // Example 1: Simple API call with error handling
  Future<void> _fetchData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await _apiService.getStudentProfile();

      if (response['status'] == 'error') {
        setState(() {
          _errorMessage = ApiErrorHandler.getErrorMessage(response);
          _lastResponse = response;
        });
        
        ApiErrorHandler.logError(response, 'Fetching student profile');
        
        if (mounted) {
          ApiErrorHandler.showSnackbar(context, response);
        }
      } else {
        debugPrint('Data loaded successfully');
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Network error: ${e.toString()}';
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  // Example 2: Another API call with error handling
  Future<void> _fetchAttendance() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await _apiService.getAttendance();

      if (response['status'] == 'error') {
        if (mounted) {
          ApiErrorHandler.showSnackbar(context, response);
        }
        ApiErrorHandler.logError(response, 'Fetching attendance');
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Attendance loaded successfully!')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${e.toString()}')),
        );
      }
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Error Handling Example')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (_errorMessage != null)
              Container(
                padding: const EdgeInsets.all(12),
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  color: Colors.red[50],
                  border: Border.all(color: Colors.red[200]!),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.error_outline, color: Colors.red[700]),
                        const SizedBox(width: 8),
                        Text('Error',
                          style: TextStyle(color: Colors.red[700],
                          fontWeight: FontWeight.bold)),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(_errorMessage!),
                  ],
                ),
              ),

            if (_lastResponse != null)
              Container(
                padding: const EdgeInsets.all(8),
                color: Colors.grey[200],
                margin: const EdgeInsets.only(bottom: 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Status: ${_lastResponse!['status']}'),
                    Text('Code: ${_lastResponse!['statusCode']}'),
                    Text('HTML: ${_lastResponse!['isHtmlResponse']}'),
                  ],
                ),
              ),

            ElevatedButton.icon(
              onPressed: _isLoading ? null : _fetchData,
              icon: const Icon(Icons.refresh),
              label: const Text('Fetch Data (Test Error Handling)'),
            ),
            const SizedBox(height: 8),
            ElevatedButton.icon(
              onPressed: _isLoading ? null : _fetchAttendance,
              icon: const Icon(Icons.calendar_today),
              label: const Text('Fetch Attendance (Test Error Handling)'),
            ),
            
            const SizedBox(height: 24),
            
            const Text('Features:',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 4),
            const Text('• Checks HTTP status code before parsing JSON'),
            const Text('• Detects HTML responses (404, 500, etc.)'),
            const Text('• Validates content-type header'),
            const Text('• Catches JSON parsing errors gracefully'),
            const Text('• Provides user-friendly error messages'),
            const Text('• Logs detailed error information'),
            const Text('• Never crashes with FormatException'),
          ],
        ),
      ),
    );
  }
}