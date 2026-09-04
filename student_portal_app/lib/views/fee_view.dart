import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';
import '../controllers/student_controller.dart';
import '../models/fee_model.dart';
import '../utils/formatters.dart';
import '../widgets/shimmer_placeholders.dart';

class FeeView extends StatefulWidget {
  const FeeView({super.key});

  @override
  State<FeeView> createState() => _FeeViewState();
}

class _FeeViewState extends State<FeeView> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    // Default to the monthly breakdown tab so the paid/pending schedule is
    // visible immediately when opening the Fee Management screen.
    _tabController = TabController(length: 2, vsync: this, initialIndex: 0);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final studentCtrl = context.watch<StudentController>();
    final feeData = studentCtrl.feeData;
    final profile = studentCtrl.profile;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: RefreshIndicator(
        onRefresh: () async {
          await studentCtrl.fetchFees();
        },
        child: Column(
          children: [
            // Header Financial Balance Summary Card
            Padding(
              padding: const EdgeInsets.all(16.0),
              child: Card(
                elevation: 4,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text('Yearly Expected', style: TextStyle(fontSize: 12, color: Colors.grey)),
                                const SizedBox(height: 2),
                                FittedBox(
                                  fit: BoxFit.scaleDown,
                                  alignment: Alignment.centerLeft,
                                  child: Text(
                                    Format.rupees(feeData?.yearlyExpected),
                                    maxLines: 1,
                                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.end,
                              children: [
                                const Text(
                                  'Current Year Paid',
                                  textAlign: TextAlign.right,
                                  style: TextStyle(fontSize: 12, color: Colors.grey),
                                ),
                                const SizedBox(height: 2),
                                FittedBox(
                                  fit: BoxFit.scaleDown,
                                  alignment: Alignment.centerRight,
                                  child: Text(
                                    Format.rupees(feeData?.currYearPaid),
                                    maxLines: 1,
                                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.green),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const Divider(height: 24),
                      // Vertical layout + FittedBox: amounts scale down instead
                      // of causing "RIGHT OVERFLOWED BY …" on narrow screens.
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Outstanding Balance:', style: TextStyle(fontWeight: FontWeight.bold)),
                          const SizedBox(height: 4),
                          FittedBox(
                            fit: BoxFit.scaleDown,
                            alignment: Alignment.centerLeft,
                            child: Text(
                              Format.rupees(feeData?.yearlyPending),
                              maxLines: 1,
                              style: TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                                color: (feeData?.yearlyPending != '0.00' && feeData?.yearlyPending != '0')
                                    ? Colors.red
                                    : Colors.green,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Total Paid:', style: TextStyle(fontWeight: FontWeight.bold)),
                          const SizedBox(height: 4),
                          FittedBox(
                            fit: BoxFit.scaleDown,
                            alignment: Alignment.centerLeft,
                            child: Text(
                              Format.rupees(feeData?.totalPaidFees),
                              maxLines: 1,
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                color: Colors.green,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      // One-time Admission Fee badge
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 8,
                          ),
                          decoration: BoxDecoration(
                            color: (profile?.hasAdmissionFee ?? false)
                                ? Colors.amber.withValues(alpha: 0.18)
                                : theme.colorScheme.surfaceContainerHighest
                                    .withValues(alpha: 0.6),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Text('🧾', style: TextStyle(fontSize: 14)),
                              const SizedBox(width: 6),
                              Text(
                                'Admission Fee:',
                                style: TextStyle(
                                  fontSize: 13,
                                  color: Colors.grey[700],
                                ),
                              ),
                              const SizedBox(width: 4),
                              Flexible(
                                child: Text(
                                  (profile?.hasAdmissionFee ?? false)
                                      ? Format.rupees(profile!.admissionFee)
                                      : 'N/A (Free / Waived)',
                                  maxLines: 1,
                                  softWrap: false,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.bold,
                                    color: (profile?.hasAdmissionFee ?? false)
                                        ? Colors.amber.shade900
                                        : Colors.grey,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ).animate().fadeIn().slideY(begin: -0.1, end: 0),
            ),
  
            // Tab Bar for Switching between 12-Month Schedule and Payment History
            TabBar(
              controller: _tabController,
              tabs: const [
                Tab(text: 'Current Year Schedule'),
                Tab(text: 'Payment Receipts Log'),
              ],
            ),
  
            Expanded(
              child: TabBarView(
                controller: _tabController,
                children: [
                  // 12-Month Schedule List
                  _buildScheduleTab(
                    feeData?.monthlySchedule ?? const [],
                    studentCtrl.isLoadingFees,
                    theme,
                  ),
  
                  // Payment History Ledger List
                  _buildHistoryTab(feeData?.results ?? const [], studentCtrl.isLoadingFees, theme),
                ],
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: studentCtrl.isDownloadingStatement
            ? null
            : () => studentCtrl.downloadFeeStatement(context),
        icon: studentCtrl.isDownloadingStatement
            ? const SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
              )
            : const Icon(Icons.picture_as_pdf_rounded),
        label: Text(studentCtrl.isDownloadingStatement ? 'Downloading...' : 'Statement PDF'),
      ),
    );
  }

  Widget _buildScheduleTab(List<MonthlyScheduleItem> schedule, bool isLoading, ThemeData theme) {
    if (isLoading) {
      return const SkeletonList(itemCount: 6);
    }
    if (schedule.isEmpty) {
      return const Center(child: Text('No fee schedule available'));
    }
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: schedule.length,
      itemBuilder: (context, index) {
        final item = schedule[index];
        final isPaid = item.isPaid;

        return Card(
          margin: const EdgeInsets.only(bottom: 10),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: isPaid ? Colors.green.withValues(alpha: 0.15) : Colors.orange.withValues(alpha: 0.15),
              child: Icon(
                isPaid ? Icons.check_circle_rounded : Icons.schedule_rounded,
                color: isPaid ? Colors.green : Colors.orange,
              ),
            ),
            // Title: month name (e.g. "January 2026")
            title: Text(
              item.monthName,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            // Subtitle: fee amount (plus payment date when available)
            subtitle: Text(
              (isPaid && (item.paymentDate?.isNotEmpty ?? false))
                  ? '${Format.rupees(item.amount)}  •  Paid ${item.paymentDate}'
                  : Format.rupees(item.amount),
              style: const TextStyle(fontSize: 13),
            ),
            // Trailing: green PAID badge with check icon / red PENDING badge
            trailing: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: isPaid ? Colors.green : Colors.red,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    isPaid ? Icons.check_rounded : Icons.close_rounded,
                    color: Colors.white,
                    size: 14,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    isPaid ? 'PAID' : 'PENDING',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ).animate().fadeIn(delay: Duration(milliseconds: 50 * index));
      },
    );
  }

  Widget _buildHistoryTab(List<FeeRecord> history, bool isLoading, ThemeData theme) {
    if (isLoading) {
      return const SkeletonList(itemCount: 6);
    }
    if (history.isEmpty) {
      return const Center(child: Text('No payment history records found.'));
    }
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: history.length,
      itemBuilder: (context, index) {
        final item = history[index];
        return Card(
          margin: const EdgeInsets.only(bottom: 10),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          child: ListTile(
            leading: const CircleAvatar(
              backgroundColor: Colors.green,
              child: Icon(Icons.receipt_long_rounded, color: Colors.white),
            ),
            title: Text(
              '${item.feeMonthName} ${item.feeYear}',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            subtitle: Text('Ref: ${item.reference.isNotEmpty ? item.reference : 'N/A'} | Date: ${item.paymentDate}'),
            trailing: Text(
              Format.rupees(item.amount),
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 16,
                color: Colors.green,
              ),
            ),
          ),
        ).animate().fadeIn(delay: Duration(milliseconds: 50 * index));
      },
    );
  }
}
