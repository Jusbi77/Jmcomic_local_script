# JM漫画下载器

一个简单的命令行工具，输入漫画ID即可将 JMComic 漫画下载并合成为 PDF 文件。

参照 [astrbot_plugin_jm_downloader](https://github.com/FloatSakura/astrbot_plugin_jm_downloader) 的实现思路编写。

## 功能

- 🔍 根据漫画ID搜索并获取漫画信息（标题、作者、章节数）
- ⬇️ 逐章节下载漫画图片
- 🔄 自动将 WebP 图片转为 JPG 格式
- 📄 将所有图片合成单个 PDF 文件（A4纸张，自适应缩放）
- 🗑️ 自动清理临时图片文件
- 🌐 支持代理和Cookie配置

## 环境要求

- Python 3.8+
- Windows / macOS / Linux

## 安装

### 1. 克隆或下载本项目

```bash
git clone <your-repo-url>
cd jm_script
```

### 2. 安装依赖

```bash
pip install jmcomic Pillow reportlab
```

三个依赖的作用：

| 依赖 | 作用 |
|------|------|
| `jmcomic` | JMComic 漫画下载库，负责搜索漫画、下载图片 |
| `Pillow` | 图片处理库，负责 WebP → JPG 格式转换、图片缩放 |
| `reportlab` | PDF 生成库，负责将多张图片合成单个 PDF |

## 快速开始

```bash
python script.py
```

运行后根据提示输入漫画ID（纯数字），等待下载完成即可。

```
==================================================
  JM漫画下载器 (Comic → PDF)
  输入漫画ID即可下载
==================================================

请输入漫画ID: 350234
[INFO] 正在获取漫画信息 ID=350234 ...
[INFO] 漫画标题: 示例漫画
[INFO] 作者: 示例作者
[INFO] 章节数: 12
  [下载] 第1章 (1/12)
  [下载] 第2章 (2/12)
  ...
[INFO] 下载完成
[INFO] 开始合成PDF...
  [PDF] 共 245 张图片待合成...
  [PDF] 合成完成 → downloads/350234.pdf
[INFO] 清理临时图片文件...

==================================================
  ✓ 下载完成!
  PDF文件: downloads/350234.pdf
  文件大小: 45.23 MB
==================================================
```

PDF 文件默认输出到 `downloads/` 目录。

## 配置

在 `script.py` 顶部可以修改以下配置项：

### 代理设置

如果需要通过代理访问，设置环境变量或修改代码：

```python
PROXY = "http://127.0.0.1:7890"  # 替换为你的代理地址
```

### Cookie设置

如果有会员Cookie，在同级目录放置 `cookie.txt` 文件，脚本会自动读取。Cookie 内容示例（每行一个）：

```
token=xxxxx
```

### PDF输出目录

```python
PDF_OUTPUT_DIR = Path(__file__).parent / "downloads"
```

### 图片最大边长

控制PDF中图片的最大分辨率，超过此尺寸会自动缩放（默认 2000px）：

```python
PDF_MAX_EDGE = 2000
```

## 工作原理

```
输入漫画ID
    │
    ▼
┌──────────────────┐
│  jmcomic 客户端   │  ← 获取漫画元数据（标题、章节列表等）
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  逐章下载图片     │  ← 下载为 .webp 格式，保存到临时目录
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  图片预处理       │  ← WebP → JPG 转换 + 超尺寸等比缩放 (Pillow)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  PDF合成         │  ← 逐页居中绘制到 A4 页面 (reportlab)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  清理 & 输出      │  ← 删除临时图片，输出最终 PDF
└──────────────────┘
```

## 常见问题

### Q: 提示 `ModuleNotFoundError: No module named 'jmcomic'`

依赖未安装，运行：

```bash
pip install jmcomic Pillow reportlab
```

### Q: 下载失败 / 连接超时

可能需要科学上网。在 `script.py` 中配置代理：

```python
PROXY = "http://127.0.0.1:7890"
```

### Q: PDF文件太大

可以调低 `PDF_MAX_EDGE` 的值（如改为 1500 或 1200），牺牲清晰度换取更小的文件体积。

### Q: 如何只下载部分章节？

`script.py` 默认下载全部章节。如需自定义，可以在 `download_album()` 函数中对 `album.episode_list` 进行切片过滤。

## 项目结构

```
jm_script/
├── script.py          # 主脚本
├── README.md          # 本文件
├── cookie.txt         # (可选) Cookie文件
└── downloads/         # PDF输出目录
    └── xxxxx.pdf
```

## 许可

仅供学习交流使用，请遵守相关法律法规。

## 致谢

- [astrbot_plugin_jm_downloader](https://github.com/FloatSakura/astrbot_plugin_jm_downloader) — 本项目的实现参考
- [jmcomic](https://github.com/tonquer/jmcomic) — JMComic Python 下载库
