class MonthlyScheduleItem {
  static const List<String> _calendarMonths = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];

  final int monthNum;
  final String monthName;
  final bool isPaid;
  final String amount;
  final String? paymentDate;
  final String reference;

  MonthlyScheduleItem({
    required this.monthNum,
    required this.monthName,
    required this.isPaid,
    required this.amount,
    this.paymentDate,
    required this.reference,
  });

  factory MonthlyScheduleItem.fromJson(Map<String, dynamic> json) {
    // ---- Month label ---------------------------------------------------
    // Supports both backend shapes:
    //   A) {month_num: 1, month_name: 'January', is_paid: true, ...}
    //   B) {month: 'Jan 2026', status: 'PAID', amount: 1000.0}
    String monthName = (json['month'] ?? json['month_name'] ?? '').toString().trim();
    if (monthName.isEmpty && json['month_num'] != null) {
      final parsed = int.tryParse(json['month_num'].toString()) ?? 1;
      final int idx = (parsed - 1).clamp(0, _calendarMonths.length - 1);
      monthName = _calendarMonths[idx];
    }

    // ---- Paid flag -----------------------------------------------------
    // Shape A exposes a boolean `is_paid`; shape B exposes a string
    // `status` ('PAID' / 'PENDING').
    final bool isPaid;
    if (json['is_paid'] != null) {
      isPaid = json['is_paid'] == true ||
          json['is_paid'].toString().toLowerCase() == 'true';
    } else {
      isPaid =
          (json['status'] ?? '').toString().trim().toUpperCase() == 'PAID';
    }

    return MonthlyScheduleItem(
      monthNum: int.tryParse(json['month_num']?.toString() ?? '') ?? 1,
      monthName: monthName,
      isPaid: isPaid,
      amount: json['amount']?.toString() ?? '0.00',
      paymentDate:
          (json['payment_date'] ?? json['date'] ?? json['paid_on'])?.toString(),
      reference: json['reference']?.toString() ?? '',
    );
  }
}

class FeeRecord {
  final int id;
  final int feeMonth;
  final String feeMonthName;
  final int feeYear;
  final String amount;
  final String paymentDate;
  final String status;
  final String statusDisplay;
  final String reference;
  final bool isExtra;

  FeeRecord({
    required this.id,
    required this.feeMonth,
    required this.feeMonthName,
    required this.feeYear,
    required this.amount,
    required this.paymentDate,
    required this.status,
    required this.statusDisplay,
    required this.reference,
    required this.isExtra,
  });

  factory FeeRecord.fromJson(Map<String, dynamic> json) {
    return FeeRecord(
      id: int.tryParse(json['id']?.toString() ?? '') ?? 0,
      feeMonth: int.tryParse(json['fee_month']?.toString() ?? '') ?? 1,
      feeMonthName: json['fee_month_name']?.toString() ?? '',
      feeYear: int.tryParse(json['fee_year']?.toString() ?? '') ?? 2026,
      amount: json['amount']?.toString() ?? '0.00',
      paymentDate: json['payment_date']?.toString() ?? '',
      status: json['status']?.toString() ?? 'PAID',
      statusDisplay: json['status_display']?.toString() ?? 'Paid',
      reference: json['reference']?.toString() ?? '',
      isExtra: json['is_extra'] == true || json['is_extra'].toString() == 'true',
    );
  }
}

class FeeData {
  final String effectiveMonthlyFee;
  final String yearlyExpected;
  final String currYearPaid;
  final String yearlyPending;
  final String totalPaidFees;
  final String overallStatus;
  final List<MonthlyScheduleItem> monthlySchedule;
  final int count;
  final String? next;
  final String? previous;
  final List<FeeRecord> results;

  FeeData({
    required this.effectiveMonthlyFee,
    required this.yearlyExpected,
    required this.currYearPaid,
    required this.yearlyPending,
    required this.totalPaidFees,
    required this.overallStatus,
    required this.monthlySchedule,
    required this.count,
    this.next,
    this.previous,
    required this.results,
  });

  factory FeeData.fromJson(Map<String, dynamic> json) {
    final schedList = (json['months_schedule'] ?? json['monthly_schedule'] ?? json['schedule']) as List? ?? [];
    final resList = (json['results'] ?? json['fee_records'] ?? json['payments']) as List? ?? [];
    return FeeData(
      effectiveMonthlyFee: json['effective_monthly_fee']?.toString() ??
          json['effective_tuition']?.toString() ??
          json['tuition_fee']?.toString() ??
          json['monthly_fee']?.toString() ??
          '0.00',
      yearlyExpected: json['yearly_expected']?.toString() ?? json['annual_fee']?.toString() ?? '0.00',
      currYearPaid: json['curr_year_paid']?.toString() ?? json['year_paid']?.toString() ?? '0.00',
      yearlyPending: json['yearly_pending']?.toString() ??
          json['year_pending']?.toString() ??
          json['pending_balance']?.toString() ??
          json['balance']?.toString() ??
          '0.00',
      totalPaidFees: json['total_paid_fees']?.toString() ??
          json['total_paid']?.toString() ??
          json['paid_amount']?.toString() ??
          '0.00',
      overallStatus: json['overall_status']?.toString() ?? json['status']?.toString() ?? 'PENDING',
      monthlySchedule: schedList.map((i) => MonthlyScheduleItem.fromJson(i as Map<String, dynamic>)).toList(),
      count: int.tryParse(json['count']?.toString() ?? '') ?? 0,
      next: json['next']?.toString(),
      previous: json['previous']?.toString(),
      results: resList.map((i) => FeeRecord.fromJson(i as Map<String, dynamic>)).toList(),
    );
  }
}
