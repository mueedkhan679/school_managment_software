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

    _tabController = TabController(
      length: 2,
      vsync: this,
      initialIndex: 0,
    );
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final studentCtrl = context.watch<StudentController>();
    final feeData = studentCtrl.feeData;
    final profile = studentCtrl.profile;

    final pending =
        (feeData?.yearlyPending != '0.00' && feeData?.yearlyPending != '0');

    return Scaffold(
      backgroundColor: colorScheme.surface,

      body: RefreshIndicator(
        onRefresh: () async {
          await studentCtrl.fetchFees();
        },
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            // ------------------------------------------------------------
            // HEADER
            // ------------------------------------------------------------
            SliverToBoxAdapter(
              child: Container(
                padding: const EdgeInsets.fromLTRB(20, 22, 20, 28),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      colorScheme.primary,
                      colorScheme.primaryContainer,
                    ],
                  ),
                  borderRadius: const BorderRadius.only(
                    bottomLeft: Radius.circular(32),
                    bottomRight: Radius.circular(32),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: colorScheme.primary.withValues(alpha: 0.22),
                      blurRadius: 22,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Header title
                    Row(
                      children: [
                        Container(
                          height: 48,
                          width: 48,
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.18),
                            borderRadius: BorderRadius.circular(15),
                          ),
                          child: const Icon(
                            Icons.account_balance_wallet_rounded,
                            color: Colors.white,
                            size: 25,
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                'Fee Management',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 22,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                              const SizedBox(height: 3),
                              Text(
                                'Track your fees & payments',
                                style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.78),
                                  fontSize: 13,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 7,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.16),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                pending
                                    ? Icons.warning_amber_rounded
                                    : Icons.verified_rounded,
                                color: Colors.white,
                                size: 15,
                              ),
                              const SizedBox(width: 5),
                              Text(
                                pending ? 'Pending' : 'Clear',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 11,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 24),

                    // ----------------------------------------------------
                    // MAIN BALANCE CARD
                    // ----------------------------------------------------
                    Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.13),
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(
                          color: Colors.white.withValues(alpha: 0.16),
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Outstanding Balance',
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.75),
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 5),
                          FittedBox(
                            fit: BoxFit.scaleDown,
                            alignment: Alignment.centerLeft,
                            child: Text(
                              Format.rupees(feeData?.yearlyPending),
                              style: TextStyle(
                                color: pending ? Colors.white : Colors.white,
                                fontSize: 34,
                                fontWeight: FontWeight.w900,
                                letterSpacing: -0.5,
                              ),
                            ),
                          ),
                          const SizedBox(height: 18),
                          Container(
                            height: 1,
                            color: Colors.white.withValues(alpha: 0.13),
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: _headerAmount(
                                  title: 'Yearly Expected',
                                  amount: Format.rupees(
                                    feeData?.yearlyExpected,
                                  ),
                                ),
                              ),
                              Container(
                                width: 1,
                                height: 38,
                                color: Colors.white.withValues(alpha: 0.15),
                              ),
                              Expanded(
                                child: _headerAmount(
                                  title: 'Current Year Paid',
                                  amount: Format.rupees(
                                    feeData?.currYearPaid,
                                  ),
                                  alignEnd: true,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ).animate().fadeIn().slideY(
                          begin: -0.08,
                          end: 0,
                        ),
                  ],
                ),
              ),
            ),

            // ------------------------------------------------------------
            // QUICK STATS
            // ------------------------------------------------------------
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 18, 16, 4),
                child: Row(
                  children: [
                    Expanded(
                      child: _statCard(
                        icon: Icons.check_circle_rounded,
                        title: 'Total Paid',
                        value: Format.rupees(
                          feeData?.totalPaidFees,
                        ),
                        iconColor: Colors.green,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _statCard(
                        icon: pending
                            ? Icons.pending_actions_rounded
                            : Icons.verified_rounded,
                        title: pending ? 'Pending' : 'Status',
                        value: pending ? 'Due' : 'Clear',
                        iconColor: pending ? Colors.orange : Colors.green,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // ------------------------------------------------------------
            // ADMISSION FEE
            // ------------------------------------------------------------
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 10, 16, 14),
                child: Container(
                  padding: const EdgeInsets.all(15),
                  decoration: BoxDecoration(
                    color: (profile?.hasAdmissionFee ?? false)
                        ? Colors.amber.withValues(alpha: 0.10)
                        : colorScheme.surfaceContainerHighest
                            .withValues(alpha: 0.65),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(
                      color: (profile?.hasAdmissionFee ?? false)
                          ? Colors.amber.withValues(alpha: 0.25)
                          : colorScheme.outlineVariant.withValues(alpha: 0.5),
                    ),
                  ),
                  child: Row(
                    children: [
                      Container(
                        height: 42,
                        width: 42,
                        decoration: BoxDecoration(
                          color: (profile?.hasAdmissionFee ?? false)
                              ? Colors.amber.withValues(alpha: 0.18)
                              : colorScheme.surfaceContainerHighest,
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          Icons.receipt_long_rounded,
                          color: (profile?.hasAdmissionFee ?? false)
                              ? Colors.amber.shade800
                              : Colors.grey,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Admission Fee',
                              style: TextStyle(
                                fontSize: 12,
                                color: theme.textTheme.bodySmall?.color
                                    ?.withValues(alpha: 0.65),
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              (profile?.hasAdmissionFee ?? false)
                                  ? Format.rupees(profile!.admissionFee)
                                  : 'N/A (Free / Waived)',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.w800,
                                color: (profile?.hasAdmissionFee ?? false)
                                    ? Colors.amber.shade900
                                    : Colors.grey,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Icon(
                        (profile?.hasAdmissionFee ?? false)
                            ? Icons.info_outline_rounded
                            : Icons.block_rounded,
                        size: 20,
                        color: Colors.grey.withValues(alpha: 0.65),
                      ),
                    ],
                  ),
                ),
              ),
            ),

            // ------------------------------------------------------------
            // TAB BAR
            // ------------------------------------------------------------
            SliverPersistentHeader(
              pinned: true,
              delegate: _FeeTabBarDelegate(
                child: Container(
                  color: colorScheme.surface,
                  padding: const EdgeInsets.fromLTRB(
                    16,
                    4,
                    16,
                    10,
                  ),
                  child: Container(
                    height: 50,
                    decoration: BoxDecoration(
                      color: colorScheme.surfaceContainerHighest
                          .withValues(alpha: 0.55),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: TabBar(
                      controller: _tabController,
                      dividerColor: Colors.transparent,
                      indicatorSize: TabBarIndicatorSize.tab,
                      indicator: BoxDecoration(
                        color: colorScheme.primary,
                        borderRadius: BorderRadius.circular(14),
                        boxShadow: [
                          BoxShadow(
                            color: colorScheme.primary.withValues(alpha: 0.20),
                            blurRadius: 10,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      labelColor: Colors.white,
                      unselectedLabelColor: theme.textTheme.bodyMedium?.color
                          ?.withValues(alpha: 0.65),
                      labelStyle: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 12,
                      ),
                      unselectedLabelStyle: const TextStyle(
                        fontWeight: FontWeight.w500,
                        fontSize: 12,
                      ),
                      tabs: const [
                        Tab(
                          icon: Icon(
                            Icons.calendar_month_rounded,
                            size: 18,
                          ),
                          text: 'Schedule',
                        ),
                        Tab(
                          icon: Icon(
                            Icons.receipt_long_rounded,
                            size: 18,
                          ),
                          text: 'Receipts',
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),

            // ------------------------------------------------------------
            // TAB CONTENT
            // ------------------------------------------------------------
            SliverFillRemaining(
              hasScrollBody: true,
              child: TabBarView(
                controller: _tabController,
                children: [
                  _buildScheduleTab(
                    feeData?.monthlySchedule ?? const [],
                    studentCtrl.isLoadingFees,
                    theme,
                  ),
                  _buildHistoryTab(
                    feeData?.results ?? const [],
                    studentCtrl.isLoadingFees,
                    theme,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),

      // --------------------------------------------------------------
      // PDF BUTTON
      // --------------------------------------------------------------
      floatingActionButton: FloatingActionButton.extended(
        elevation: 8,
        backgroundColor: colorScheme.primary,
        onPressed: studentCtrl.isDownloadingStatement
            ? null
            : () => studentCtrl.downloadFeeStatement(context),
        icon: studentCtrl.isDownloadingStatement
            ? const SizedBox(
                width: 21,
                height: 21,
                child: CircularProgressIndicator(
                  color: Colors.white,
                  strokeWidth: 2,
                ),
              )
            : const Icon(
                Icons.picture_as_pdf_rounded,
                color: Colors.white,
              ),
        label: Text(
          studentCtrl.isDownloadingStatement
              ? 'Downloading...'
              : 'Statement PDF',
          style: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }

  // ====================================================================
  // HEADER AMOUNT
  // ====================================================================

  Widget _headerAmount({
    required String title,
    required String amount,
    bool alignEnd = false,
  }) {
    return Column(
      crossAxisAlignment:
          alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: [
        Text(
          title,
          textAlign: alignEnd ? TextAlign.right : TextAlign.left,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.70),
            fontSize: 11,
          ),
        ),
        const SizedBox(height: 4),
        FittedBox(
          fit: BoxFit.scaleDown,
          alignment: alignEnd ? Alignment.centerRight : Alignment.centerLeft,
          child: Text(
            amount,
            maxLines: 1,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w800,
              fontSize: 16,
            ),
          ),
        ),
      ],
    );
  }

  // ====================================================================
  // STAT CARD
  // ====================================================================

  Widget _statCard({
    required IconData icon,
    required String title,
    required String value,
    required Color iconColor,
  }) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        color:
            theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: theme.colorScheme.outlineVariant.withValues(alpha: 0.45),
        ),
      ),
      child: Row(
        children: [
          Container(
            height: 42,
            width: 42,
            decoration: BoxDecoration(
              color: iconColor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(13),
            ),
            child: Icon(
              icon,
              color: iconColor,
              size: 22,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 11,
                    color: theme.textTheme.bodySmall?.color
                        ?.withValues(alpha: 0.60),
                  ),
                ),
                const SizedBox(height: 3),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: Text(
                    value,
                    maxLines: 1,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      color: iconColor,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ====================================================================
  // MONTHLY SCHEDULE
  // ====================================================================

  Widget _buildScheduleTab(
    List<MonthlyScheduleItem> schedule,
    bool isLoading,
    ThemeData theme,
  ) {
    if (isLoading) {
      return const SkeletonList(itemCount: 6);
    }

    if (schedule.isEmpty) {
      return _emptyState(
        icon: Icons.calendar_month_outlined,
        title: 'No Fee Schedule',
        message: 'No monthly fee schedule is available right now.',
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
      itemCount: schedule.length,
      itemBuilder: (context, index) {
        final item = schedule[index];
        final isPaid = item.isPaid;

        return Container(
          margin: const EdgeInsets.only(bottom: 11),
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceContainerHighest
                .withValues(alpha: 0.42),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: isPaid
                  ? Colors.green.withValues(alpha: 0.16)
                  : Colors.orange.withValues(alpha: 0.16),
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.035),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(13),
            child: Row(
              children: [
                // Month icon
                Container(
                  height: 48,
                  width: 48,
                  decoration: BoxDecoration(
                    color: isPaid
                        ? Colors.green.withValues(alpha: 0.11)
                        : Colors.orange.withValues(alpha: 0.11),
                    borderRadius: BorderRadius.circular(15),
                  ),
                  child: Icon(
                    isPaid
                        ? Icons.check_circle_rounded
                        : Icons.schedule_rounded,
                    color: isPaid ? Colors.green : Colors.orange,
                    size: 25,
                  ),
                ),

                const SizedBox(width: 13),

                // Month + Amount
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.monthName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 15,
                        ),
                      ),
                      const SizedBox(height: 5),
                      Text(
                        Format.rupees(item.amount),
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: theme.textTheme.bodyMedium?.color
                              ?.withValues(alpha: 0.65),
                        ),
                      ),
                      if (isPaid &&
                          (item.paymentDate?.isNotEmpty ?? false)) ...[
                        const SizedBox(height: 3),
                        Row(
                          children: [
                            Icon(
                              Icons.event_available_rounded,
                              size: 13,
                              color: Colors.green.withValues(alpha: 0.75),
                            ),
                            const SizedBox(width: 4),
                            Flexible(
                              child: Text(
                                'Paid ${item.paymentDate}',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Colors.green.withValues(alpha: 0.85),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),

                const SizedBox(width: 8),

                // Status badge
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 7,
                  ),
                  decoration: BoxDecoration(
                    color: isPaid
                        ? Colors.green.withValues(alpha: 0.12)
                        : Colors.red.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        isPaid ? Icons.check_rounded : Icons.close_rounded,
                        color: isPaid ? Colors.green : Colors.red,
                        size: 14,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        isPaid ? 'PAID' : 'PENDING',
                        style: TextStyle(
                          color: isPaid ? Colors.green : Colors.red,
                          fontSize: 10,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        )
            .animate()
            .fadeIn(
              delay: Duration(milliseconds: 45 * index),
            )
            .slideX(
              begin: 0.04,
              end: 0,
            );
      },
    );
  }

  // ====================================================================
  // PAYMENT HISTORY
  // ====================================================================

  Widget _buildHistoryTab(
    List<FeeRecord> history,
    bool isLoading,
    ThemeData theme,
  ) {
    if (isLoading) {
      return const SkeletonList(itemCount: 6);
    }

    if (history.isEmpty) {
      return _emptyState(
        icon: Icons.receipt_long_outlined,
        title: 'No Payment Records',
        message: 'Your payment history will appear here.',
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
      itemCount: history.length,
      itemBuilder: (context, index) {
        final item = history[index];

        return Container(
          margin: const EdgeInsets.only(bottom: 11),
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceContainerHighest
                .withValues(alpha: 0.42),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: Colors.green.withValues(alpha: 0.14),
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.035),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                // Receipt icon
                Container(
                  height: 48,
                  width: 48,
                  decoration: BoxDecoration(
                    color: Colors.green.withValues(alpha: 0.11),
                    borderRadius: BorderRadius.circular(15),
                  ),
                  child: const Icon(
                    Icons.receipt_long_rounded,
                    color: Colors.green,
                    size: 24,
                  ),
                ),

                const SizedBox(width: 13),

                // Payment information
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${item.feeMonthName} ${item.feeYear}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 5),
                      Row(
                        children: [
                          const Icon(
                            Icons.calendar_today_rounded,
                            size: 12,
                            color: Colors.grey,
                          ),
                          const SizedBox(width: 4),
                          Flexible(
                            child: Text(
                              item.paymentDate,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 11,
                                color: theme.textTheme.bodySmall?.color
                                    ?.withValues(alpha: 0.65),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          const Icon(
                            Icons.tag_rounded,
                            size: 13,
                            color: Colors.grey,
                          ),
                          const SizedBox(width: 3),
                          Expanded(
                            child: Text(
                              item.reference.isNotEmpty
                                  ? item.reference
                                  : 'N/A',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 11,
                                color: theme.textTheme.bodySmall?.color
                                    ?.withValues(alpha: 0.55),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),

                const SizedBox(width: 8),

                // Amount
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'PAID',
                      style: TextStyle(
                        fontSize: 9,
                        fontWeight: FontWeight.w900,
                        color: Colors.green.withValues(alpha: 0.8),
                      ),
                    ),
                    const SizedBox(height: 3),
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Text(
                        Format.rupees(item.amount),
                        style: const TextStyle(
                          color: Colors.green,
                          fontSize: 15,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        )
            .animate()
            .fadeIn(
              delay: Duration(milliseconds: 45 * index),
            )
            .slideX(
              begin: 0.04,
              end: 0,
            );
      },
    );
  }

  // ====================================================================
  // EMPTY STATE
  // ====================================================================

  Widget _emptyState({
    required IconData icon,
    required String title,
    required String message,
  }) {
    final theme = Theme.of(context);

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(30),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              height: 78,
              width: 78,
              decoration: BoxDecoration(
                color: theme.colorScheme.primary.withValues(alpha: 0.08),
                shape: BoxShape.circle,
              ),
              child: Icon(
                icon,
                size: 36,
                color: theme.colorScheme.primary.withValues(alpha: 0.65),
              ),
            ),
            const SizedBox(height: 18),
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 7),
            Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 13,
                color:
                    theme.textTheme.bodyMedium?.color?.withValues(alpha: 0.55),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ======================================================================
// PINNED TAB BAR DELEGATE
// ======================================================================

class _FeeTabBarDelegate extends SliverPersistentHeaderDelegate {
  final Widget child;

  _FeeTabBarDelegate({
    required this.child,
  });

  @override
  double get minExtent => 64;

  @override
  double get maxExtent => 64;

  @override
  Widget build(
    BuildContext context,
    double shrinkOffset,
    bool overlapsContent,
  ) {
    return child;
  }

  @override
  bool shouldRebuild(covariant _FeeTabBarDelegate oldDelegate) {
    return oldDelegate.child != child;
  }
}
