# vscode_dev_env

个人 VSCode 项目模板库：为每个技术栈提供一套开箱即用的 `.vscode` 工作区配置。

## 目录结构

```
vscode_dev_env/
├── .gitignore                  # 模板库自身的忽略规则
└── templates/
    ├── _base/
    │   └── settings.common.json  # 跨栈通用设置（规范文档，不拷贝进项目）
├── python-vscode/.vscode/    # Python 专属
├── node-vscode/.vscode/      # JS / TS / Node 专属
├── vue-vscode/.vscode/       # Vue 专属
├── react-vscode/.vscode/     # React 专属
├── miniprogram-vscode/.vscode/  # 微信小程序专属
├── go-vscode/.vscode/        # Go 专属
├── rust-vscode/.vscode/      # Rust 专属
└── markdown-vscode/.vscode/  # Markdown 文档专属
```

## 使用方式

新建项目时，直接复制对应栈的整个目录内容到项目根目录：

```powershell
# 示例：初始化一个 Python 项目
Copy-Item -Recurse "E:\kuoleroy\vscode_dev_env\templates\python-vscode\." "C:\你的项目\"
```

然后按需安装推荐的扩展（VSCode 会在打开 `extensions.json` 时自动提示）。

## 模板内容

每个栈的 `.vscode` 包含四个文件：

| 文件 | 说明 |
| --- | --- |
| `settings.json` | 完整可生效的工作区设置（含通用 + 栈专属） |
| `launch.json` | 调试配置：运行 / 附加调试 |
| `tasks.json` | 常用任务：dev、build、test、lint |
| `extensions.json` | 推荐扩展列表 |

### settings.json 结构约定

所有栈的 `settings.json` 均为「完整版」，直接拷入项目即可生效，分两个分区：

1. **① 通用设置** — 取自 `_base/settings.common.json`，跨栈共享，勿单独修改；
2. **② 栈专属设置** — 标注「覆盖通用项」和「新增项」，差异一目了然。

> `_base/settings.common.json` 只作为模板仓库内的规范文档，不拷贝进项目；
> 如需调整通用部分，修改该文件后同步到各栈的 ① 区即可。

## 各栈要点

| 栈 | 格式化 | 其他 |
| --- | --- | --- |
| python | ruff（4 空格，88 列视觉标尺） | pytest、.venv 解释器 |
| node | prettier | eslint、tsdk 指向本地 typescript |
| vue | Volar | eslint 校验 .vue，tsdk 本地 |
| react | prettier | eslint（jsx/tsx），tsdk 本地 |
| miniprogram | prettier（JS/JSON）+ minapp（WXML） | DevTools CLI 任务、jest 单测 |
| go | gofmt（Go 扩展，Tab 缩进） | dlv 调试（本地/远程）、go test/vet |
| rust | rustfmt（rust-analyzer，4 空格） | cargo 任务、LLDB 调试（二进制名按提示填写） |
| markdown | Markdown All in One | markdownlint 任务、失效链接检查、Mermaid 预览 |

## 其他说明

- `settings.json` / `launch.json` / `tasks.json` 是 JSONC 格式（允许注释）；
- `extensions.json` 是严格 JSON（不允许注释）；
- 调试 Chrome 时无需手动启动 dev server：`launch.json` 内置 `serverReadyAction`，等待终端输出启动地址后自动打开调试器。
- 微信小程序：页面调试在微信开发者工具内进行；`tasks.json` 的 CLI 任务（打开项目 / 构建 npm / 预览 / 上传）需要先开启开发者工具「设置 → 安全设置 → 服务端口」，并在 `settings.json` 的 `miniprogram.cliPath` 配置 cli.bat 路径（Windows 默认安装路径已预填）。