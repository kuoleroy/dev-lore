# tag-audio 使用说明

批量把元信息（标题 / 演唱者 / 专辑 / 流派 / 日期 / 音轨号 / 注释）写入音频文件（FLAC、MP3）。
基于 Python `mutagen` 库，**完全离线运行**，不依赖网络，也不依赖任何第三方 GUI（如 Kid3）。

---

## 环境依赖

- Python 3.8+（`run.bat` 已写死用 `C:\Users\admin\miniconda3\envs\aligner` 下的 `python.exe`）
- 必须安装 `mutagen`：`pip install mutagen`
  - 若该环境的 python 没有 mutagen，双击 `run.bat` 会报 `ModuleNotFoundError: No module named 'mutagen'`

## 目录文件

```
tag-audio/
├─ tag_audio.py    # 主脚本：读 metadata.json，逐首写标签
├─ run.bat        # Windows 双击入口（指向 aligner 环境 python）
└─ metadata.json  # 歌单与元信息，你日常只需要改这个
```

## 快速开始（3 步）

1. 用记事本 / 任意编辑器打开 `metadata.json`
2. 按下方字段说明，填好每首歌的 `file`（音频路径）和元信息
3. 双击 `run.bat`（或在命令行跑 `python tag_audio.py`）

脚本逐首写入，结束打印：`完成：N/M 首写入成功。`

## metadata.json 字段

顶层必须是一个**列表（数组）**，每首歌一个对象：

| 字段 | 必填 | 说明 |
|---|---|---|
| `file` | 是 | 音频文件路径。支持绝对路径，或相对本目录的相对路径 |
| `title` | 否 | 曲名（TITLE） |
| `artist` | 否 | 演唱者 / 艺名（ARTIST） |
| `album` | 否 | 专辑名（ALBUM） |
| `genre` | 否 | 流派（GENRE），如 `工业 dub / 雷鬼` |
| `date` | 否 | 年份或日期（DATE），如 `2026` 或 `2026-10-27` |
| `tracknumber` | 否 | 音轨号（整数，如 `1`）；不填则不写该标签 |
| `comment` | 否 | 注释 / 简介（COMMENT） |

- 缺失字段写入空字符串，不会报错。
- `tracknumber` 不填则跳过该标签。

## 完整示例

```json
[
  {
    "file": "C:\\Users\\admin\\Desktop\\相交一次\\相交一次.flac",
    "title": "相交一次",
    "artist": "你的艺名",
    "album": "几何的安排",
    "genre": "中文独立 / 阶级悲歌",
    "date": "2026",
    "tracknumber": 1,
    "comment": "两条相交线，相交一次就再也回不来。"
  },
  {
    "file": "无情相交线.flac",
    "title": "无情相交线",
    "artist": "你的艺名",
    "album": "几何的安排",
    "genre": "工业 dub / 雷鬼",
    "date": "2026",
    "tracknumber": 2,
    "comment": "流水线上的两条相交线，被齿轮的洪流冲散。"
  }
]
```

> 上面第二首用相对路径 `无情相交线.flac`，等价于把它放在 `tag_audio.py` 同目录。

## 支持的音频格式

| 格式 | 标签标准 | 备注 |
|---|---|---|
| `FLAC` | Vorbis Comments | 写入 TITLE/ARTIST/ALBUM/GENRE/DATE/COMMENT/TRACKNUMBER |
| `MP3` | ID3v2 | 写入 TIT2/TPE1/TALB/TCON/TDRC/COMM/TRCK；COMM 语言设为 `chi` |
| 其他 | — | wav/m4a 等暂不支持，会跳过并提示 `不支持格式` |

## 注意事项

- **艺名 / 专辑待定**：当前 `metadata.json` 里 `artist` / `album` 是占位符 `【艺名待定】` / `【专辑名待定】`，定下来后替换即可。
- 路径含中文、空格均没问题；相对路径相对于 `tag_audio.py` 所在目录解析。
- 写入为**覆盖式**：只更新列出的字段，不会删掉文件里其他已存在的标签。
- 想一次只处理部分歌：把 `metadata.json` 暂不处理的项删掉即可，下次再补。
- 换 Python 环境：编辑 `run.bat` 里的 `ENV` 变量指向新环境的 `python.exe`。

## 验证写入

任意标签查看器都能检查：
- Windows：右键文件 → 属性 → 详细信息
- 播放器：foobar2000、VLC（右键 → 信息 / 媒体信息）
- 命令行：`python -c "import mutagen; print(mutagen.File('路径'))"`

> 注：Kid3 这类 GUI 在本机因 SteamTools 代理拦截官方下载源暂时装不动；本项目脚本在功能上已覆盖其"写标签"需求。

## 常见问题

| 现象 | 原因 / 解决 |
|---|---|
| `ModuleNotFoundError: mutagen` | aligner 环境没装。运行 `C:\Users\admin\miniconda3\envs\aligner\python.exe -m pip install mutagen` |
| `找不到文件: ...` | `file` 路径写错；检查绝对路径或相对位置是否正确 |
| `不支持格式（只支持 flac/mp3）` | 当前只支持这两种，其他格式请先转码 |
| 双击一闪而过 | 正常结束会显示"按回车退出"；若报错被吞，改用命令行 `python tag_audio.py` 看完整输出 |
