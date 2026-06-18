import 'package:flutter/material.dart';
import 'screens/connect_screen.dart';

void main() => runApp(const BlurArcApp());

class BlurArcApp extends StatelessWidget {
  const BlurArcApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Blur Arc',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(useMaterial3: true).copyWith(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF22D3EE),
          brightness: Brightness.dark,
        ),
      ),
      home: const ConnectScreen(),
    );
  }
}
