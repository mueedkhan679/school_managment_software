Write-Host "Cleaning Flutter Project..." -ForegroundColor Yellow
flutter clean

Write-Host "Getting Dependencies..." -ForegroundColor Yellow
flutter pub get

Write-Host "Running App on Connected Device..." -ForegroundColor Green
flutter run