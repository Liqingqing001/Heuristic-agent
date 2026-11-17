# -*- coding: utf-8 -*-
"""校验 20 页版本，并用渲染出的 PNG 重新生成预览图与总览图。"""
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.util import Inches

REPORT = Path(r"D:\dsh工作\智育助教\Heuristic-agent\docs\reports")
OUT = REPORT / "2026-11-17/output"
PPTX = OUT / "Zhiyu_Stage_Report_2026-11-17.pptx"
RENDERED = Path(sys.argv[1])

prs = Presentation(PPTX)
assert len(prs.slides) == 20, len(prs.slides)

problems = []
for i, slide in enumerate(prs.slides, 1):
    footer = None
    for sh in slide.shapes:
        if sh.has_text_frame and abs(sh.left - Inches(12.05)) < 150000 and abs(sh.top - Inches(7.09)) < 150000:
            footer = sh.text_frame.text.strip()
    if footer != f"{i:02d}":
        problems.append(f"第 {i} 页页脚是 {footer!r}")
    if not slide.notes_slide.notes_text_frame.text.strip():
        problems.append(f"第 {i} 页缺备注")
    for sh in slide.shapes:
        assert sh.left >= 0 and sh.top >= 0, (i, sh.name)
        assert sh.left + sh.width <= prs.slide_width + 10, (i, sh.name, "宽")
        assert sh.top + sh.height <= prs.slide_height + 10, (i, sh.name, "高")

print("页数:", len(prs.slides), "| 页脚/备注问题:", problems or "无")

files = sorted(RENDERED.glob("*.png"))
assert len(files) == 20, len(files)

prev = OUT / "previews"
for old in prev.glob("slide-*.png"):
    old.unlink()
for i, file in enumerate(files, 1):
    shutil.copy(file, prev / f"slide-{i:02d}.png")
print("previews 已更新:", len(files), "张")

thumbs = []
for file in files:
    im = Image.open(file).convert("RGB")
    im.thumbnail((360, 203))
    thumbs.append(im)
sheet = Image.new("RGB", (1480, 5 * 233 + 20), "#E8EDF5")
d = ImageDraw.Draw(sheet)
for i, im in enumerate(thumbs):
    x = 20 + (i % 4) * 365
    y = 20 + (i // 4) * 233
    sheet.paste(im, (x, y))
    d.text((x + 8, y + 206), f"{i + 1:02d}", fill="#20324E")
sheet.save(OUT / "slides-overview.png")
print("slides-overview.png 已重生成")
