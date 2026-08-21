#!/usr/bin/env python3
import json
import os
import re
import sys
import urllib.request

AUTHOR_URL = "https://app.ahcjzs.cn/"
DATA_JSON = "appstore.json"

CAT_MAP = {
    "1地图导航": "导航地图",
    "2影音播放": "影音视听",
    "3影视浏览": "影视浏览",
    "4互联投屏": "手车互联",
    "5实用工具": "实用工具",
    "6GAC插件": "GAC插件",
    "7其它应用": "其他应用",
    "8版本升级": "版本升级",
    "测试专区": "测试专区",
}


def fetch():
    req = urllib.request.Request(
        AUTHOR_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "ignore")


def parse(content):
    pattern = re.compile(
        r'<div class="app-card">(.*?)</div>\s*(?=<div class="app-card">|$)', re.DOTALL
    )
    cards = pattern.findall(content)

    def get_text(card, cls):
        m = re.search(r'<div class="' + cls + r'">(.*?)</div>', card, re.DOTALL)
        return m.group(1).strip() if m else ""

    apps = []
    for card in cards:
        name = get_text(card, "app-name")
        if not name or name == "看文字介绍":
            continue

        typ = get_text(card, "app-type")
        version_info = get_text(card, "app-version")
        desc = get_text(card, "app-description")
        desc = re.sub(r"\s+", " ", desc).strip()

        ver = version_info
        size = ""
        m = re.match(r"(.*?)[┃┆|](.*)$", version_info)
        if m:
            ver = m.group(1).strip()
            size = m.group(2).strip()

        icon = re.search(r'<img src="([^"]+)"', card)
        icon_url = icon.group(1) if icon else ""

        dl = re.search(r"window\.location\.href = '([^']*)'", card)
        dl_url = dl.group(1).strip() if dl else ""
        if dl_url:
            dl_url = re.sub(r"^(删除|xx|X)", "", dl_url).strip()
        if not dl_url or dl_url == "xx":
            continue

        cat_name = CAT_MAP.get(typ, typ)
        apps.append(
            {
                "cat": cat_name,
                "name": name,
                "version": ver,
                "size": size,
                "description": desc,
                "icon": icon_url,
                "url": dl_url,
            }
        )

    categories = {}
    for a in apps:
        categories.setdefault(a["cat"], []).append(
            {
                "name": a["name"],
                "version": a["version"],
                "description": a["description"],
                "size": a["size"],
                "icon": a["icon"],
                "url": a["url"],
            }
        )

    cat_order = [
        "导航地图",
        "影音视听",
        "影视浏览",
        "手车互联",
        "实用工具",
        "GAC插件",
        "其他应用",
        "版本升级",
        "测试专区",
    ]
    output = {
        "version": "1.0",
        "updateTime": "",
        "categories": [
            {"name": c, "apps": categories[c]}
            for c in cat_order
            if c in categories
        ],
    }
    return output


def main():
    try:
        content = fetch()
    except Exception as e:
        print(f"抓取作者页面失败: {e}")
        sys.exit(0)

    try:
        new_data = parse(content)
    except Exception as e:
        print(f"解析应用列表失败: {e}")
        sys.exit(0)

    new_total = sum(len(c["apps"]) for c in new_data["categories"])
    print(f"解析到 {new_total} 个应用")

    old_data = None
    if os.path.exists(DATA_JSON):
        with open(DATA_JSON, "r", encoding="utf-8") as f:
            old_data = json.load(f)

    if old_data is None:
        old_total = 0
        print("首次运行，生成初始数据")
    else:
        old_total = sum(len(c["apps"]) for c in old_data["categories"])
        old_compare = {k: v for k, v in old_data.items() if k != "updateTime"}
        new_compare = {k: v for k, v in new_data.items() if k != "updateTime"}
        if old_compare == new_compare:
            print("无变化")
            sys.exit(0)
        print(f"有变化: {old_total} -> {new_total}")

    import datetime
    new_data["updateTime"] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    with open(DATA_JSON + ".tmp", "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    os.replace(DATA_JSON + ".tmp", DATA_JSON)


if __name__ == "__main__":
    main()