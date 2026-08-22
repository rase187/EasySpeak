#!/usr/bin/env python3
"""
Generate PNG assets and animated GIF from logo.svg using PyQt6 (already installed)
"""
import sys
import os
sys.path.insert(0, r"D:\EasySpeak")

from PyQt6.QtCore import Qt, QSize, QByteArray, QTimer
from PyQt6.QtGui import QImage, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication
from PIL import Image
import io

# Create QApplication if needed
app = QApplication.instance() or QApplication(sys.argv)

ASSETS_DIR = r"D:\EasySpeak\assets"
SVG_PATH = os.path.join(ASSETS_DIR, "logo.svg")

# PNG sizes needed
SIZES = [16, 24, 32, 48, 64, 128, 256]

def generate_pngs():
    """Generate PNG files at multiple sizes"""
    print("Generating PNGs...")
    renderer = QSvgRenderer(SVG_PATH)

    for size in SIZES:
        # Create image with transparent background
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(QColor(0, 0, 0, 0))  # Transparent

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        renderer.render(painter)
        painter.end()

        # Save
        png_path = os.path.join(ASSETS_DIR, f"logo_{size}.png")
        image.save(png_path)
        print(f"  OK {size}x{size}")

def generate_animated_gif():
    """Generate animated GIF by rendering frames with different animation states"""
    print("Generating animated GIF...")

    renderer = QSvgRenderer(SVG_PATH)
    frames = []
    num_frames = 30
    gif_size = 256

    for i in range(num_frames):
        # Progress through animation cycle (0.0 to 1.0)
        progress = i / num_frames

        # Create a modified SVG with static frame at this progress
        # We'll create the frame manually by drawing
        image = QImage(gif_size, gif_size, QImage.Format.Format_ARGB32)
        image.fill(QColor(0x1e, 0x1e, 0x2e, 255))  # Catppuccin base

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Scale to fit
        painter.scale(gif_size / 128.0, gif_size / 128.0)

        # Draw base
        painter.setPen(QColor(0x45, 0x47, 0x5a))
        painter.setBrush(QColor(0x1e, 0x1e, 0x2e))
        painter.drawRoundedRect(0, 0, 128, 128, 24, 24)

        # Draw animated element
        painter.translate(64, 64)

        # Gradient color interpolation
        # progress 0: recording red (#f7768e), progress 1: sapphire (#74c7ec)
        r = int(0xf7 * (1 - progress) + 0x74 * progress)
        g = int(0x76 * (1 - progress) + 0xc7 * progress)
        b = int(0x8e * (1 - progress) + 0xec * progress)
        color = QColor(r, g, b)

        painter.setPen(color)
        # Pen width scaled
        pen = painter.pen()
        pen.setWidth(4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        # Press line
        line_progress = progress
        dash_len = 32 * line_progress
        gap_len = 32 * (1 - line_progress)
        # Simple approach: draw partial line
        line_y2 = -32 + (32 * line_progress)
        painter.drawLine(0, -32, 0, int(line_y2))

        # Expanding waves
        for wave_idx, (max_radius, base_opacity, delay) in enumerate([
            (28, 0.8, 0),
            (22, 0.6, 0.15),
            (16, 0.4, 0.3),
        ]):
            wave_progress = max(0, progress - delay)
            if wave_progress > 0:
                opacity = base_opacity * (1 - wave_progress)
                color.setAlpha(int(255 * opacity))
                painter.setPen(color)

                # Draw wave arc
                rect_size = int(max_radius * wave_progress * 2)
                if rect_size > 0:
                    # Draw the wave path: M-r,0 Q0,-h r,0
                    # Approximate with arc
                    from PyQt6.QtCore import QRectF
                    wave_rect = QRectF(-max_radius * wave_progress, -max_radius * wave_progress,
                                       max_radius * wave_progress * 2, max_radius * wave_progress * 2)
                    # Draw upper arc (the wave)
                    painter.drawArc(wave_rect, 0, 180 * 16)  # Qt uses 1/16 degree

        painter.end()

        # Convert to PIL Image
        buffer = QByteArray()
        buffer_io = io.BytesIO()
        # Save to QBuffer first
        from PyQt6.QtCore import QBuffer, QIODevice
        qbuffer = QBuffer(buffer)
        qbuffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(qbuffer, "PNG")
        qbuffer.close()
        pil_img = Image.open(io.BytesIO(bytes(buffer)))
        frames.append(pil_img.convert('RGBA'))

    gif_path = os.path.join(ASSETS_DIR, "logo.gif")
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=80,
        loop=0,
        optimize=True,
        disposal=2
    )
    print(f"  OK logo.gif ({num_frames} frames)")

def generate_favicon():
    """Generate favicon.ico with multiple sizes"""
    print("Generating favicon.ico...")
    ico_path = os.path.join(ASSETS_DIR, "favicon.ico")
    images = []
    for size in [16, 32, 48]:
        png_path = os.path.join(ASSETS_DIR, f"logo_{size}.png")
        images.append(Image.open(png_path))
    images[0].save(ico_path, format='ICO', sizes=[(16,16), (32,32), (48,48)])
    print(f"  OK favicon.ico")

if __name__ == "__main__":
    generate_pngs()
    generate_animated_gif()
    generate_favicon()
    print("\nOK All assets generated!")