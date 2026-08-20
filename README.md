# 应用商店配置说明

## 文件说明

- `appstore.json` — 应用商店数据文件，编辑这个文件即可更新应用
- `icons/` — 应用图标文件夹，把图标放这里

## 如何添加应用

在 `appstore.json` 的 `apps` 数组里添加一个应用：

```json
{
  "name": "应用名称",
  "version": "v1.0.0",
  "description": "应用描述",
  "category": "tools",
  "icon": "icons/应用图标.png",
  "downloadUrl": "https://下载地址.apk"
}
```

## 如何添加分类

在 `appstore.json` 的 `categories` 数组里添加：

```json
{"id": "newcat", "name": "新分类"}
```

然后把应用的 `category` 字段改成 `newcat` 就会归到这个分类。

## category 字段说明

- `all` — 全部应用（特殊分类，自动显示所有应用）
- 其他分类的 `id` 和应用的 `category` 字段对应

## icon 字段说明

图标文件放在 `icons/` 文件夹里，路径写 `icons/文件名.png`。
推荐尺寸 200x200，PNG格式。

## 修改后生效

修改 `appstore.json` 并推送到 GitHub 后，应用打开应用商店会自动拉取最新数据。
