import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import 'controllers/auth_controller.dart';
import 'controllers/student_controller.dart';
import 'controllers/teacher_controller.dart';
import 'views/login_view.dart';
import 'views/main_scaffold_view.dart';
import 'views/teacher_dashboard_view.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const StudentPortalApp());
}

class StudentPortalApp extends StatelessWidget {
  const StudentPortalApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthController()),
        ChangeNotifierProvider(create: (_) => StudentController()),
        ChangeNotifierProvider(create: (_) => TeacherController()),
      ],
      child: Consumer<AuthController>(
        builder: (context, auth, _) {
          Widget home;
          if (auth.isAuthenticated) {
            final session = auth.session;
            if (session != null && session.role == 'TEACHER') {
              home = const TeacherDashboardView();
            } else {
              home = const MainScaffoldView();
            }
          } else {
            home = const LoginView();
          }
          return MaterialApp(
            title: 'School Portal',
            debugShowCheckedModeBanner: false,
            theme: ThemeData(
              useMaterial3: true,
              colorSchemeSeed: Colors.indigo,
              brightness: Brightness.light,
              textTheme: GoogleFonts.poppinsTextTheme(ThemeData.light().textTheme),
            ),
            darkTheme: ThemeData(
              useMaterial3: true,
              colorSchemeSeed: Colors.indigo,
              brightness: Brightness.dark,
              textTheme: GoogleFonts.poppinsTextTheme(ThemeData.dark().textTheme),
            ),
            themeMode: ThemeMode.system,
            home: home,
          );
        },
      ),
    );
  }
}

