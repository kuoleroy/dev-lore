# 匹配"数字 + 紧跟非数字非下划线非点字符"，插入下划线
# 例如：004中后台 -> 004_中后台，029uni-app -> 029_uni-app
Get-ChildItem -File | ForEach-Object {
    $file = $_.Name
    if ($file -match '^(\d+)([^0-9_.])') {
        $newName = $file -replace '^(\d+)([^0-9_.])', '$1_$2'
        Rename-Item $_.FullName -NewName $newName
        Write-Host "已重命名: $file -> $newName"
    }
}

Write-Host "全部处理完成！" -ForegroundColor Green
