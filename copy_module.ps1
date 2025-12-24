# Script để copy module eCommerce vào thư mục addons
# Sử dụng: .\copy_module.ps1 -SourcePath "ĐƯỜNG_DẪN_ĐẾN_MODULE"

param(
    [Parameter(Mandatory=$true)]
    [string]$SourcePath
)

$TargetPath = ".\addons"

# Kiểm tra thư mục nguồn có tồn tại không
if (-not (Test-Path $SourcePath)) {
    Write-Host "Lỗi: Không tìm thấy thư mục module tại: $SourcePath" -ForegroundColor Red
    exit 1
}

# Lấy tên thư mục module
$ModuleName = Split-Path -Leaf $SourcePath

# Đường dẫn đích
$DestinationPath = Join-Path $TargetPath $ModuleName

# Kiểm tra xem module đã tồn tại trong addons chưa
if (Test-Path $DestinationPath) {
    Write-Host "Cảnh báo: Module '$ModuleName' đã tồn tại trong thư mục addons!" -ForegroundColor Yellow
    $overwrite = Read-Host "Bạn có muốn ghi đè không? (y/n)"
    if ($overwrite -ne "y" -and $overwrite -ne "Y") {
        Write-Host "Đã hủy thao tác." -ForegroundColor Yellow
        exit 0
    }
    Remove-Item -Path $DestinationPath -Recurse -Force
}

# Copy module
Write-Host "Đang copy module '$ModuleName' vào thư mục addons..." -ForegroundColor Green
Copy-Item -Path $SourcePath -Destination $DestinationPath -Recurse -Force

if (Test-Path $DestinationPath) {
    Write-Host "Thành công! Module '$ModuleName' đã được copy vào: $DestinationPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "Bước tiếp theo:" -ForegroundColor Cyan
    Write-Host "1. Restart Odoo container: docker-compose restart odoo" -ForegroundColor Cyan
    Write-Host "2. Vào Odoo -> Apps -> Update Apps List" -ForegroundColor Cyan
    Write-Host "3. Tìm và cài đặt module '$ModuleName'" -ForegroundColor Cyan
} else {
    Write-Host "Lỗi: Không thể copy module!" -ForegroundColor Red
    exit 1
}

