import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'screens/connect_screen.dart';
import 'services/theme_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final themeProvider = ThemeProvider();
  await themeProvider.load();
  runApp(BlurArcApp(themeProvider: themeProvider));
}

class BlurArcApp extends StatelessWidget {
  final ThemeProvider themeProvider;

  const BlurArcApp({super.key, required this.themeProvider});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: themeProvider,
      builder: (context, _) {
        final themeProvider = context.watch<ThemeProvider>();
        return MaterialApp(
          title: 'Blur Arc',
          debugShowCheckedModeBanner: false,
          themeMode: themeProvider.mode,
          darkTheme: themeProvider.getThemeData(Brightness.dark),
          theme: themeProvider.getThemeData(Brightness.light),
          home: const ConnectScreen(),
        );
      },
    );
  }
}
