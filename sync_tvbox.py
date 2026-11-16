#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
饭太硬 / aiwex 聚合影视源 → 干净镜像脚本

做什么：
  1. 拉取上游配置（默认 https://9280.kstore.vip/aiwex.json）
  2. 去掉里面的推广/提示内容：
       - 顶层 log（公告日志）、ads（广告位）
       - sites 里那些本质是广告位的条目（名字是「免费分享」「切勿上当」「更新日期」之类）
       - sites 里的 notice / announcement 字段
  3. 其余原样保留：sites 的真实站点、parses、lives、doh、rules、headers、spider
  4. 输出 tvbox.json（给 TVBox/FongMi/我听听 直接填的地址）
  5. 内容没变化就不写文件，方便 GitHub Actions 只在真的更新时才提交

用法：
  python3 sync_tvbox.py                # 用默认上游
  python3 sync_tvbox.py --src URL      # 换上游
  python3 sync_tvbox.py --dry-run      # 只看会删什么，不写文件
"""

import argparse
import io
import json
import os
import sys
import urllib.request

DEFAULT_SRC = "https://9280.kstore.vip/aiwex.json"
OUT_NAME = "tvbox.json"
REMOVED_NAME = "removed.txt"

UA = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")

# 名字里出现这些词，基本就是广告位/公告位，不是能看的站点
PROMO_WORDS = (
    "切勿上当", "免费分享", "本接口", "接口免费", "加群", "QQ群", "qq群",
    "域名配置", "站点域名", "正在下载", "仅供学习", "请勿传播",
    "更新日期", "公告", "通知", "打赏", "赞助", "广告", "推广",
)

# 这些顶层字段是推广/装饰用的，镜像里不需要
DROP_TOP_KEYS = ("log", "ads")


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def is_promo_site(site):
    name = str(site.get("name", ""))
    if any(w in name for w in PROMO_WORDS):
        return True
    # 名字里几乎全是装饰符号和括号内容，且没有真实 api —— 典型的广告占位
    core = "".join(ch for ch in name if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")
    api = str(site.get("api", ""))
    if not api and len(core) <= 2:
        return True
    return False


def clean(cfg):
    removed = []

    for k in DROP_TOP_KEYS:
        if k in cfg:
            removed.append("顶层字段 %s（%d 字）" % (k, len(json.dumps(cfg[k], ensure_ascii=False))))
            cfg.pop(k, None)

    sites = cfg.get("sites", [])
    kept = []
    for s in sites:
        if is_promo_site(s):
            removed.append("站点 [%s] name=%s" % (s.get("key", "?"), s.get("name", "")))
            continue
        # 站点里自带的公告字段一并去掉，保留其它参数
        changed = False
        for f in ("notice", "announcement", "announce", "ad"):
            if f in s:
                s.pop(f, None)
                changed = True
        if changed:
            removed.append("站点 [%s] 去掉公告字段" % s.get("key", "?"))
        kept.append(s)
    cfg["sites"] = kept

    # parses / lives 里同样可能塞公告
    for section in ("parses", "lives"):
        for item in cfg.get(section, []) or []:
            if isinstance(item, dict):
                for f in ("notice", "announcement", "ad"):
                    item.pop(f, None)

    return cfg, removed


def dump(cfg):
    # 与上游一致的 4 空格缩进，diff 更好读
    return json.dumps(cfg, ensure_ascii=False, indent=4) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--out", default=OUT_NAME)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--drop-spider",
        action="store_true",
        help="连 spider（那个伪装成 .jpg 的 jar）一起删。删了配置最干净，"
             "但这个源的站点全靠这个 jar，删完 csp_* 站点会大面积失效，按需使用",
    )
    args = ap.parse_args()

    raw = fetch(args.src)
    try:
        cfg = json.loads(raw)
    except Exception as e:
        print("上游不是 JSON，可能换了地址或加了密：%s" % e, file=sys.stderr)
        return 2

    before = len(cfg.get("sites", []))
    cfg, removed = clean(cfg)
    if args.drop_spider and cfg.get("spider"):
        removed.append("顶层字段 spider（%s）" % str(cfg["spider"])[:60])
        cfg.pop("spider", None)
    after = len(cfg.get("sites", []))
    cfg["_mirror"] = {
        "src": args.src,
        "note": "镜像自上游，已去掉推广/公告内容；只保留可用的影视站点与直播源",
    }

    text = dump(cfg)

    print("上游站点 %d → 保留 %d，去掉 %d 条内容" % (before, after, len(removed)))
    for line in removed:
        print("  - " + line)

    if args.dry_run:
        print("dry-run：不写文件")
        return 0

    changed = True
    if os.path.exists(args.out):
        old = io.open(args.out, encoding="utf-8").read()
        # _mirror 里的 src 一样、正文一样才算没变化
        changed = old != text

    if not changed:
        print("上游没有实质变化，跳过写入（GitHub Actions 不会产生空提交）")
        return 0

    io.open(args.out, "w", encoding="utf-8").write(text)
    io.open(REMOVED_NAME, "w", encoding="utf-8").write("\n".join(removed) + "\n")
    print("已写入 %s（%d 字节）" % (args.out, len(text.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
