"""Optional Windows/Linux system tray. Requires requirements-tray.txt."""
from __future__ import annotations

import threading


def start(open_url: str, shutdown, title: str = 'ToolForge V1.2'):
    """Start a tray icon in a background thread; return False when pystray is absent."""
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:
        return False
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((6, 6, 58, 58), radius=14, fill=(118, 96, 211, 255))
    draw.rectangle((16, 18, 24, 48), fill=(241, 242, 248, 255))
    draw.rectangle((28, 24, 34, 48), fill=(241, 242, 248, 255))
    draw.rectangle((38, 30, 44, 48), fill=(241, 242, 248, 255))

    def open_action(icon, item):
        import webbrowser
        webbrowser.open(open_url)

    def quit_action(icon, item):
        icon.stop()
        shutdown()

    menu = pystray.Menu(
        pystray.MenuItem('ToolForge öffnen', open_action, default=True),
        pystray.MenuItem('Beenden', quit_action),
    )
    icon = pystray.Icon('toolforge', image, title, menu)
    threading.Thread(target=icon.run, daemon=True).start()
    return True
