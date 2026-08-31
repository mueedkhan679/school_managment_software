import 'package:flutter/material.dart';
import '../services/api_service.dart';

class NotificationCenterView extends StatefulWidget {
  const NotificationCenterView({super.key});

  @override
  State<NotificationCenterView> createState() => _NotificationCenterViewState();
}

class _NotificationCenterViewState extends State<NotificationCenterView> {
  final ApiService _api = ApiService();
  bool _isLoading = true;
  String? _error;
  List<dynamic> _notifications = [];

  @override
  void initState() {
    super.initState();
    _fetchNotifications();
  }

  Future<void> _fetchNotifications() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final res = await _api.getNotifications();
      if (res['status'] == 'success') {
        setState(() {
          _notifications = res['payload'] ?? [];
        });
      } else {
        setState(() => _error = res['message'] ?? 'Failed to load notifications');
      }
    } catch (e) {
      setState(() => _error = 'An error occurred.');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _clearAll() async {
    setState(() => _isLoading = true);
    try {
      final res = await _api.clearNotifications();
      if (!mounted) return;
      if (res['status'] == 'success') {
        setState(() {
          _notifications = [];
        });
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(res['message'] ?? 'Failed to clear')),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('An error occurred')),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          if (_notifications.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.clear_all),
              tooltip: 'Clear All',
              onPressed: _clearAll,
            ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!, style: const TextStyle(color: Colors.red)))
              : _notifications.isEmpty
                  ? const Center(child: Text('No new notifications'))
                  : ListView.builder(
                      itemCount: _notifications.length,
                      itemBuilder: (context, index) {
                        final n = _notifications[index];
                        final msg = n['message'] ?? '';
                        final date = n['created_at'] != null 
                            ? DateTime.tryParse(n['created_at'])?.toLocal().toString().split('.')[0] 
                            : '';
                        return Card(
                          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                          child: ListTile(
                            leading: const Icon(Icons.notifications_active, color: Colors.blue),
                            title: Text(msg),
                            subtitle: Text(date ?? ''),
                          ),
                        );
                      },
                    ),
    );
  }
}
