# -*- coding: utf-8 -*-
"""批量把元信息写入音频文件（FLAC / MP3）。
读取同目录的 metadata.json（一个列表，每项一首歌），自动识别格式并写入标签。
运行：双击 run.bat，或 python tag_audio.py
"""
import json
import os

from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, TDRC, COMM, TRCK

HERE = os.path.dirname(os.path.abspath(__file__))


def load_list():
    p = os.path.join(HERE, "metadata.json")
    if not os.path.isfile(p):
        sys_exit("找不到 metadata.json，请把它放在本目录。")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def sys_exit(msg):
    import sys
    print(msg)
    input("按回车退出…")
    sys.exit(1)


def tag_flac(path, m):
    a = FLAC(path)
    a["TITLE"] = m.get("title", "")
    a["ARTIST"] = m.get("artist", "")
    a["ALBUM"] = m.get("album", "")
    a["GENRE"] = m.get("genre", "")
    a["DATE"] = m.get("date", "")
    a["COMMENT"] = m.get("comment", "")
    if m.get("tracknumber"):
        a["TRACKNUMBER"] = str(m["tracknumber"])
    a.save()


def tag_mp3(path, m):
    a = MP3(path, ID3=ID3)
    try:
        a.add_tags()
    except Exception:
        pass
    a.tags.add(TIT2(encoding=3, text=m.get("title", "")))
    a.tags.add(TPE1(encoding=3, text=m.get("artist", "")))
    a.tags.add(TALB(encoding=3, text=m.get("album", "")))
    a.tags.add(TCON(encoding=3, text=m.get("genre", "")))
    a.tags.add(TDRC(encoding=3, text=m.get("date", "")))
    a.tags.add(COMM(encoding=3, lang="chi", desc="", text=m.get("comment", "")))
    if m.get("tracknumber"):
        a.tags.add(TRCK(encoding=3, text=str(m["tracknumber"])))
    a.save()


def main():
    items = load_list()
    if not isinstance(items, list):
        sys_exit("metadata.json 顶层必须是一个列表（数组）。")
    ok = 0
    for m in items:
        f = m.get("file", "")
        if not os.path.isabs(f):
            f = os.path.join(HERE, f)
        if not os.path.isfile(f):
            print("✗ 找不到文件:", f)
            continue
        ext = f.lower().rsplit(".", 1)[-1]
        try:
            if ext == "flac":
                tag_flac(f, m)
            elif ext == "mp3":
                tag_mp3(f, m)
            else:
                print("✗ 不支持格式（只支持 flac/mp3）:", f)
                continue
            print("✓ 已写入:", m.get("title", f))
            ok += 1
        except Exception as e:
            print("✗ 失败:", f, "->", e)
    print("\n完成：%d/%d 首写入成功。" % (ok, len(items)))
    input("按回车退出…")


if __name__ == "__main__":
    main()
