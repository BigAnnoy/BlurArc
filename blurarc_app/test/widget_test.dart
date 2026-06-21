import 'package:flutter_test/flutter_test.dart';
import 'package:blurarc_app/main.dart';
import 'package:blurarc_app/services/theme_provider.dart';

void main() {
  testWidgets('BlurArcApp renders connection screen', (WidgetTester tester) async {
    await tester.pumpWidget(BlurArcApp(themeProvider: ThemeProvider()));
    // Should show app title somewhere
    expect(find.text('Blur Arc'), findsWidgets);
  });
}
