# Quick Start Guide: Robust JSON Error Handling

## 🎯 What Was Fixed

Your Flutter app was crashing with `FormatException: Unexpected character (at character 1) <!DOCTYPE html>` when the backend returned HTML instead of JSON.

**Solution:** Enhanced `ApiService._processResponse()` to safely handle HTML responses, validate content-type, and catch JSON parsing errors gracefully.

## 📁 Files Changed

1. **`lib/services/api_service.dart`** - Enhanced `_processResponse()` method
2. **`lib/utils/api_error_handler.dart`** - NEW utility for error handling
3. **`lib/utils/error_handling_example.dart`** - NEW example implementation
4. **`JSON_ERROR_HANDLING_SOLUTION.md`** - NEW detailed documentation

## 🚀 How to Use (Quick Examples)

### 1. Basic Error Handling in Any API Call

```dart
final response = await apiService.getStudentProfile();

if (response['status'] == 'error') {
  // Show user-friendly error
  ApiErrorHandler.showSnackbar(context, response);
  
  // Log for debugging
  ApiErrorHandler.logError(response, 'getStudentProfile');
  return;
}

// Success - use response data
```

### 2. Different Error Display Options

```dart
// Simple snackbar (most common)
ApiErrorHandler.showSnackbar(context, response);

// Detailed dialog (for HTML errors)
if (response['isHtmlResponse'] == true) {
  ApiErrorHandler.showErrorDialog(context, response);
}

// Get just the message
String message = ApiErrorHandler.getErrorMessage(response);
```

### 3. In Your Existing Controllers

Update your controller methods to handle the new error structure:

```dart
Future<void> fetchProfile() async {
  final res = await _apiService.getStudentProfile();
  
  if (res['status'] == 'error') {
    _profileError = ApiErrorHandler.getErrorMessage(res);
    
    // Optional: show snackbar
    if (mounted) {
      ApiErrorHandler.showSnackbar(context, res);
    }
    
    notifyListeners();
    return;
  }
  
  // Success path
  final payload = res['payload'] != null ? res['payload'] : res;
  _profile = StudentProfile.fromJson(payload);
  notifyListeners();
}
```

## 🔍 What Information You Get

Every error response now includes:

```dart
{
  'status': 'error',
  'message': 'User-friendly message',
  'statusCode': 404,              // HTTP status code
  'rawBody': '...',               // Raw response (first 500 chars in logs)
  'isHtmlResponse': true,         // Was it an HTML page?
  'parseError': '...',            // JSON parse error (if applicable)
}
```

## 🛡️ What Errors Are Now Handled

- ✅ **404 Not Found** - Endpoint doesn't exist
- ✅ **500 Internal Server Error** - Server crashed
- ✅ **503 Service Unavailable** - Server down for maintenance
- ✅ **Invalid JSON** - Response is not valid JSON
- ✅ **Wrong Content-Type** - Response is not JSON
- ✅ **Network Errors** - Connection issues
- ✅ **Successful responses** - 2xx status codes still work normally

## 📱 Testing the Solution

### Test with a non-existent endpoint:
```dart
// This will now show a friendly error instead of crashing
final response = await http.get(Uri.parse('https://mueed563.pythonanywhere.com/api/non-existent/'));
final result = _processResponse(response);
// result['status'] == 'error'
// result['statusCode'] == 404
// result['isHtmlResponse'] == true
```

### Test with invalid JSON:
```dart
// Backend returns plain text instead of JSON
// Old code: CRASHES with FormatException
// New code: Returns error object with parseError details
```

## 🎨 Customizing Error Messages

Edit `lib/utils/api_error_handler.dart`:

```dart
static String _getHtmlErrorSuggestion(int? statusCode) {
  switch (statusCode) {
    case 404: return 'Your custom 404 message here';
    case 500: return 'Your custom 500 message here';
    // ... etc
  }
}
```

## 📊 Debugging Improvements

All API calls now log:
```
Response Status Code: 404
Response Content-Type: text/html
Response Body (first 500 chars): <!DOCTYPE html>...
⚠️ Server returned HTML instead of JSON
```

## 🔧 Troubleshooting

### Q: I'm still seeing FormatException
**A:** Make sure you're using the updated `api_service.dart` file. The fix is in the `_processResponse()` method.

### Q: How do I see the detailed logs?
**A:** Run your app in debug mode and check the console. All API responses are logged with `debugPrint()`.

### Q: Can I disable the detailed logging?
**A:** Yes, remove or comment out the `debugPrint()` calls in `_processResponse()` method.

### Q: Will this affect my existing code?
**A:** No, it's backward compatible. Successful responses (2xx) work exactly the same. Only error responses now include more information.

## 📚 More Details

See `JSON_ERROR_HANDLING_SOLUTION.md` for:
- Complete technical explanation
- All error scenarios handled
- Migration guide for existing code
- Best practices for error handling

## ✅ Verification

To verify the fix is working:

1. Run your app
2. Try to access a non-existent API endpoint
3. Check console logs - you should see detailed error information
4. App should NOT crash - instead, you'll get an error object
5. User sees a friendly error message (if you use `ApiErrorHandler`)

---

**Need help?** Check the example file: `lib/utils/error_handling_example.dart`