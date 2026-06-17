"""
JM漫画下载器 - 根据ID搜索并下载漫画为PDF
参照: https://github.com/FloatSakura/astrbot_plugin_jm_downloader

用法:
  python script.py            # 交互模式，提示输入ID
  python script.py 350234     # 直接传ID下载
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path
from io import BytesIO
from typing import Optional

# Windows下强制UTF-8编码，避免中文输出乱码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ============================================================
# 第三方库导入
# ============================================================
try:
    import jmcomic
    from jmcomic import JmModuleConfig, JmOption
except ImportError:
    print("[ERROR] 请先安装 jmcomic: pip install jmcomic")
    sys.exit(1)

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:
    print("[ERROR] 请先安装 Pillow: pip install Pillow")
    sys.exit(1)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas as rl_canvas
except ImportError:
    print("[ERROR] 请先安装 reportlab: pip install reportlab")
    sys.exit(1)


# ============================================================
# 配置
# ============================================================
PROXY = os.environ.get("JM_PROXY", None)                # 代理, 如 "http://127.0.0.1:7890"
COOKIE_FILE = Path(__file__).parent / "cookie.txt"      # Cookie文件
PDF_OUTPUT_DIR = Path(__file__).parent / "downloads"    # PDF输出目录
PHOTO_TMP_DIR = Path(__file__).parent / ".photo_tmp"    # 图片临时目录
PDF_MAX_EDGE = 2000                                      # PDF图片最大边长(像素)
PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 工具函数 - WebP/JPG图片处理
# ============================================================

def webp_to_jpg_bytes(photo_path: str, max_edge: int = PDF_MAX_EDGE) -> Optional[BytesIO]:
    """将图片转为JPG字节流(BytesIO)，并根据最大边长等比缩放"""
    try:
        img = Image.open(photo_path)
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        width, height = img.size
        max_dim = max(width, height)
        if max_dim > max_edge:
            ratio = max_edge / max_dim
            img = img.resize((int(width * ratio), int(height * ratio)), Image.LANCZOS)

        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)  # 重置指针，否则 ImageReader 从末尾读不到数据
        return buf
    except (FileNotFoundError, UnidentifiedImageError, OSError) as e:
        print(f"[WARN] 图片转换失败 {photo_path}: {e}")
        return None


# ============================================================
# PDF合成
# ============================================================

def images_to_pdf(photo_dir: str, output_path: str, max_edge: int = PDF_MAX_EDGE):
    """将目录下所有图片(递归子目录)合成为一个PDF文件"""
    # 递归收集所有图片文件
    photo_files = []
    for root, dirs, files in os.walk(photo_dir):
        dirs.sort()  # 按目录名排序保证章节顺序
        for f in sorted(files, key=lambda x: int("".join(filter(str.isdigit, x)) or 0)):
            if f.lower().endswith((".webp", ".jpg", ".jpeg", ".png")):
                photo_files.append(os.path.join(root, f))

    if not photo_files:
        raise FileNotFoundError(f"目录中没有找到图片文件: {photo_dir}")

    print(f"  [PDF] 共 {len(photo_files)} 张图片待合成...")

    c = rl_canvas.Canvas(output_path, pagesize=A4)
    page_w, page_h = A4

    for i, filepath in enumerate(photo_files):
        jpg_data = webp_to_jpg_bytes(filepath, max_edge=max_edge)
        if jpg_data is None:
            print(f"  [PDF] 跳过无法转换的图片: {os.path.basename(filepath)}")
            continue

        try:
            reader = ImageReader(jpg_data)
            img_w, img_h = reader.getSize()
            ratio = min(page_w / img_w, page_h / img_h)
            draw_w, draw_h = img_w * ratio, img_h * ratio
            c.drawImage(reader, (page_w - draw_w) / 2, (page_h - draw_h) / 2,
                        width=draw_w, height=draw_h)
            c.showPage()

            if (i + 1) % 20 == 0:
                print(f"  [PDF] 进度: {i + 1}/{len(photo_files)}")
        except Exception as e:
            print(f"  [PDF] 处理图片失败 {os.path.basename(filepath)}: {e}")
            continue

    c.save()
    print(f"  [PDF] 合成完成 → {output_path}")


# ============================================================
# 漫画下载核心
# ============================================================

def _build_option(base_dir: str, cookie: Optional[str] = None) -> JmOption:
    """构建 jmcomic JmOption (适配 jmcomic 2.x)"""

    # 组装 Cookie headers
    headers = None
    if cookie:
        headers = {"Cookie": cookie}

    # 代理
    proxies = PROXY if PROXY else JmModuleConfig.DEFAULT_PROXIES

    return JmOption(
        dir_rule={
            "rule": "Bd_Pname",
            "base_dir": base_dir,
        },
        download={
            "cache": True,
            "image": {"decode": True, "suffix": ".webp"},
            "threading": {
                "image": 30,
                "photo": os.cpu_count() or 4,
            },
        },
        client={
            "cache": None,
            "domain": [],
            "postman": {
                "type": "curl_cffi",
                "meta_data": {
                    "impersonate": "chrome",
                    "headers": headers,
                    "proxies": proxies,
                },
            },
            "impl": "api",
            "retry_times": 5,
        },
        plugins={"valid": "log"},
        call_after_init_plugin=False,
    )


async def download_album(album_id: str) -> str:
    """下载指定漫画ID的所有章节, 返回图片目录路径"""

    # 读取 Cookie
    cookie = None
    if COOKIE_FILE.exists():
        cookie = COOKIE_FILE.read_text(encoding="utf-8").strip().replace("\n", "; ")
        if not cookie:
            cookie = None

    # 清理并创建临时目录
    if PHOTO_TMP_DIR.exists():
        shutil.rmtree(PHOTO_TMP_DIR)
    PHOTO_TMP_DIR.mkdir(parents=True, exist_ok=True)

    base_dir = str(PHOTO_TMP_DIR)

    # 1. 创建 option + client（用于获取元数据）
    option = _build_option(base_dir, cookie)
    client = option.build_jm_client()

    # 2. 获取漫画信息
    print(f"[INFO] 正在获取漫画信息 ID={album_id} ...")
    album = await asyncio.to_thread(client.get_album_detail, album_id)

    title = album.title or album_id
    print(f"[INFO] 漫画标题: {title}")
    print(f"[INFO] 作者: {album.author}")
    print(f"[INFO] 章节数: {len(album.episode_list)}")

    # 3. 下载整个album (jmcomic 会自动下载所有章节)
    print(f"[INFO] 开始下载...")
    await asyncio.to_thread(option.download_album, album_id)

    print(f"[INFO] 下载完成，图片保存在: {base_dir}")
    return base_dir


# ============================================================
# 主流程
# ============================================================

async def main(album_id: str = None):
    print("=" * 50)
    print("  JM漫画下载器 (Comic → PDF)")
    print("=" * 50)
    print()

    # 获取漫画ID
    if album_id is None:
        if len(sys.argv) > 1:
            album_id = sys.argv[1].strip()
        else:
            album_id = input("请输入漫画ID: ").strip()

    if not album_id:
        print("[ERROR] 漫画ID不能为空")
        print("用法: python script.py [漫画ID]")
        return

    if not album_id.isdigit():
        print("[ERROR] 漫画ID应为纯数字")
        return

    try:
        # 1. 下载漫画
        photo_dir = await download_album(album_id)

        # 2. 合成PDF（webp临时文件保留，下次下载时自动清理）
        pdf_path = str(PDF_OUTPUT_DIR / f"{album_id}.pdf")
        print(f"\n[INFO] 开始合成PDF...")
        images_to_pdf(photo_dir, pdf_path)

        # 3. 输出结果
        pdf_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        print(f"\n{'=' * 50}")
        print(f"  ✓ 下载完成!")
        print(f"  PDF文件: {pdf_path}")
        print(f"  文件大小: {pdf_size_mb:.2f} MB")
        print(f"{'=' * 50}")

    except Exception as e:
        print(f"\n[ERROR] 下载失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
