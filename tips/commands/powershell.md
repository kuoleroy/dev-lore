# 常用 CLI 小工具

## 提取 HTML class 生成 CSS 骨架

```sh
npx extract-classnames --src ./index.html --dest ./index.css
```

## 启动临时静态服务器

```powershell
npx http-server ./dist -p 3000
```

## 图片压缩

```sh
npx imagemin ./images/* --out-dir=./compressed
```

## 汉字竖排显示

```powershell
# 竖排显示
"xx xx xx" -split '\s+' -join "`n"

# 竖排直接设置到剪贴板
"xx xx xx" -split '\s+' -join "`n" | Set-Clipboard
```
