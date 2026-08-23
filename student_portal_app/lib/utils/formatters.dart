/// Lightweight formatting helpers shared across views.
///
/// Intentionally dependency-free (no `intl`) so it can be used anywhere
/// without adding a direct dependency.
class Format {
  Format._();

  /// Formats a raw numeric string (e.g. `'10000'`, `'10000.0'`, `'10,000.00'`)
  /// as a grouped currency amount: `Rs 10,000.00`.
  ///
  /// Falls back to `Rs 0.00` when [amount] is null or unparsable.
  static String rupees(String? amount, {String symbol = 'Rs '}) {
    final cleaned = (amount ?? '').replaceAll(',', '').trim();
    final value = double.tryParse(cleaned) ?? 0.0;
    return '$symbol${_group(value.toStringAsFixed(2))}';
  }

  /// Inserts thousands separators into the integer part of a string that is
  /// already fixed to 2 decimal places (e.g. `'10000.00'` → `'10,000.00'`).
  static String _group(String twoDecimal) {
    final parts = twoDecimal.split('.');
    final digits = parts[0];
    final sign = digits.startsWith('-') ? '-' : '';
    final unsigned = sign.isEmpty ? digits : digits.substring(1);

    final buffer = StringBuffer(sign);
    for (int i = 0; i < unsigned.length; i++) {
      buffer.write(unsigned[i]);
      final remaining = unsigned.length - i - 1;
      if (remaining > 0 && remaining % 3 == 0) {
        buffer.write(',');
      }
    }
    return '${buffer.toString()}.${parts.length > 1 ? parts[1] : '00'}';
  }
}