# ==============================================================================
# سكريبت تصفير وإعادة تهيئة قواعد البيانات (Local SQLite + Supabase)
# ==============================================================================

Write-Host "Resetting local database..." -ForegroundColor Cyan

# 1. حذف ملفات قاعدة البيانات المحلية القديمة
$dbFiles = @(
    "$PSScriptRoot\..\api\annotations.db",
    "$PSScriptRoot\..\annotations.db"
)

foreach ($file in $dbFiles) {
    if (Test-Path $file) {
        Remove-Item -Path $file -Force
        Write-Host "  Deleted: $file" -ForegroundColor Yellow
    }
}

Write-Host "  Local SQLite database wiped clean." -ForegroundColor Green
Write-Host ""
Write-Host "======================================================================" -ForegroundColor Magenta
Write-Host "To wipe all Supabase tables in cloud:" -ForegroundColor Magenta
Write-Host "======================================================================" -ForegroundColor Magenta
Write-Host "1. Open Supabase Dashboard: https://supabase.com/dashboard"
Write-Host "2. Go to your project -> SQL Editor."
Write-Host "3. Copy the content from: supabase/drop_all_tables.sql"
Write-Host "4. Paste and click RUN."
Write-Host "5. All old tables will be dropped cleanly."
Write-Host "Backup of old migrations is saved at: archive/supabase-backup/"
Write-Host "======================================================================" -ForegroundColor Magenta
