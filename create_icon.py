"""生成应用图标"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    # 创建 256x256 图标
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 背景圆角矩形
    padding = 20
    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=40,
        fill='#1e1e1e'
    )
    
    # 绘制 "D" 字母
    try:
        font = ImageFont.truetype("arial.ttf", 140)
    except:
        font = ImageFont.load_default()
    
    # 渐变色 D
    text = "D"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 20
    
    # 绘制文字
    draw.text((x, y), text, fill='#0d6efd', font=font)
    
    # 底部小点装饰（代表服务状态）
    dot_y = size - 60
    colors = ['#28a745', '#ffc107', '#dc3545']
    for i, color in enumerate(colors):
        dot_x = size // 2 - 40 + i * 40
        draw.ellipse([dot_x - 8, dot_y - 8, dot_x + 8, dot_y + 8], fill=color)
    
    # 保存为 ICO
    icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
    
    # 创建多尺寸图标
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icons = [img.resize(s, Image.Resampling.LANCZOS) for s in sizes]
    
    icons[0].save(icon_path, format='ICO', sizes=[(s[0], s[1]) for s in sizes], append_images=icons[1:])
    print(f"图标已保存: {icon_path}")
    
    return icon_path

if __name__ == "__main__":
    create_icon()
