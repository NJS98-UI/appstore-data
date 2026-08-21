#!/usr/bin/env python3
import json
import os
import re
import sys
import urllib.request

AUTHOR_URL = "https://app.ahcjzs.cn/"
DATA_JSON = "appstore.json"
AUTHOR_SNAPSHOT = "docs/latest_author.json"

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

    download_icons(new_data)
    if new_data["categories"]:
        # 只有图标路径变化但数据没变时，也要更新文件
        pass

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
            write_snapshot(new_data)
            sys.exit(0)
        print(f"有变化: {old_total} -> {new_total}")

    import datetime
    new_data["updateTime"] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    with open(DATA_JSON + ".tmp", "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    os.replace(DATA_JSON + ".tmp", DATA_JSON)

    write_snapshot(new_data)


def write_snapshot(data):
    try:
        author_apps = []
        for cat in data["categories"]:
            for a in cat["apps"]:
                author_apps.append({
                    "name": a["name"],
                    "version": a["version"],
                    "type": cat["name"],
                })
        snapshot = {
            "updateTime": data["updateTime"],
            "appCount": len(author_apps),
            "apps": author_apps,
        }
        os.makedirs("docs", exist_ok=True)
        with open(AUTHOR_SNAPSHOT, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存快照失败: {e}")


def download_icons(data):
    import urllib.parse
    icons_dir = "icons"
    os.makedirs(icons_dir, exist_ok=True)
    existing = set(os.listdir(icons_dir))
    downloaded = 0
    for cat in data["categories"]:
        for app in cat["apps"]:
            url = app.get("icon", "")
            if not url or url.startswith("icons/"):
                continue
            m = re.search(r"/app/icon/(.+)$", url)
            if not m:
                continue
            fname = re.sub(r'[\\/:*?"<>|]', "_", m.group(1))
            target = os.path.join(icons_dir, fname)
            if fname in existing and os.path.isfile(target):
                app["icon"] = "icons/" + fname
                continue
            try:
                parsed = urllib.parse.urlparse(url)
                encoded_path = urllib.parse.quote(parsed.path, safe='/:@!$&\'()*+,;=-._~')
                encoded_url = urllib.parse.urlunparse(parsed._replace(path=encoded_path))
                req = urllib.request.Request(encoded_url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://app.ahcjzs.cn/"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    raw = r.read()
                if len(raw) >= 50:
                    with open(target, "wb") as f:
                        f.write(raw)
                    app["icon"] = "icons/" + fname
                    downloaded += 1
                    existing.add(fname)
            except Exception as e:
                print(f"  图标下载失败: {url} -> {e}")
    if downloaded > 0:
        print(f"下载新图标: {downloaded} 个")


if __name__ == "__main__":
    main()