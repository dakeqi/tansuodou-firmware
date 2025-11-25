# 推送固件源码到GitHub并触发构建

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  推送固件到GitHub tansuodou-firmware仓库" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. 检查当前状态
Write-Host "`n[步骤 1/5] 检查本地Git状态..." -ForegroundColor Yellow
git status --short

# 2. 检查是否已经有远程仓库配置
Write-Host "`n[步骤 2/5] 检查远程仓库配置..." -ForegroundColor Yellow
$remotes = git remote
if ($remotes -contains "origin") {
    Write-Host "✅ 远程仓库已配置: origin" -ForegroundColor Green
    git remote -v
} else {
    Write-Host "⚠️ 未配置远程仓库，正在添加..." -ForegroundColor Yellow
    git remote add origin https://github.com/dakeqi/tansuodou-firmware.git
    Write-Host "✅ 已添加远程仓库: https://github.com/dakeqi/tansuodou-firmware.git" -ForegroundColor Green
}

# 3. 添加并提交所有未提交的更改
Write-Host "`n[步骤 3/5] 提交本地更改..." -ForegroundColor Yellow
git add -A
$commitResult = git commit -m "firmware: v3.1.1 - 品牌名称修正 + 版本一致性修复" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 提交成功" -ForegroundColor Green
} else {
    if ($commitResult -match "nothing to commit") {
        Write-Host "✅ 无需提交，工作树干净" -ForegroundColor Green
    } else {
        Write-Host "⚠️ 提交失败: $commitResult" -ForegroundColor Yellow
    }
}

# 4. 推送到GitHub
Write-Host "`n[步骤 4/5] 推送到GitHub..." -ForegroundColor Yellow
Write-Host "正在推送到 origin/master..." -ForegroundColor Cyan
git push origin master
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 推送成功！" -ForegroundColor Green
} else {
    Write-Host "❌ 推送失败，请检查网络连接和GitHub权限" -ForegroundColor Red
    exit 1
}

# 5. 显示GitHub Actions链接
Write-Host "`n[步骤 5/5] GitHub Actions构建状态" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ 代码已成功推送到GitHub！" -ForegroundColor Green
Write-Host "`n📋 GitHub Actions 正在自动构建固件..." -ForegroundColor Yellow
Write-Host "🔗 查看构建状态:" -ForegroundColor Cyan
Write-Host "   https://github.com/dakeqi/tansuodou-firmware/actions" -ForegroundColor White
Write-Host "`n⏰ 预计构建时间: 5-10分钟" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "💡 提示：构建完成后，执行以下命令同步固件到本地：" -ForegroundColor Cyan
Write-Host "   cd c:\Users\89762\TCD\tansuodou-firmware" -ForegroundColor White
Write-Host "   git pull origin master" -ForegroundColor White
Write-Host "   Copy-Item binaries\*.bin c:\Users\89762\TCD\tansuodou-v2\frontend\public\firmware\binaries\ -Force`n" -ForegroundColor White
