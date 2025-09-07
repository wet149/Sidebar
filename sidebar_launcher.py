# sidebar_launcher.py

import tkinter as tk
from tkinter import filedialog
import os
import json
import subprocess
import threading
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

# --- Настройки ---
CONFIG_FILE = "sidebar_config.json"

# Параметры по умолчанию
DEFAULT_CONFIG = {
    "side": "right",           # "left" или "right"
    "color": "#4B2E2A",        # Тёмно-коричневый
    "width_collapsed": 16,     # Только стрелка
    "width_expanded": 200,
    "show_tray": True
}

# Загружаем конфиг
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            CONFIG = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in CONFIG:
                    CONFIG[k] = v
    except:
        CONFIG = DEFAULT_CONFIG.copy()
else:
    CONFIG = DEFAULT_CONFIG.copy()

# Переменные
SIDEBAR_WIDTH_COLLAPSED = CONFIG["width_collapsed"]   # Только стрелка
SIDEBAR_WIDTH_EXPANDED = CONFIG["width_expanded"]
BG_COLOR = CONFIG["color"]
SIDE = CONFIG["side"]  # "left" или "right"
ANIMATION_STEP = 6
ANIMATION_DELAY = 10

class SidebarLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.98)

        # Экран
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        # Состояние
        self.current_width = SIDEBAR_WIDTH_COLLAPSED
        self.is_expanded = False
        self.animation_running = False

        # Позиция
        self.update_position()

        # Фон
        self.root.config(bg=BG_COLOR)

        # Canvas для стрелки
        self.canvas = tk.Canvas(
            self.root,
            width=SIDEBAR_WIDTH_COLLAPSED,
            height=self.screen_height - 40,
            bg=BG_COLOR,
            highlightthickness=0
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.Y)
        self.draw_arrow()

        # Кнопки (скрыты до раскрытия)
        self.button_frame = tk.Frame(self.root, bg="#5A3A35", width=SIDEBAR_WIDTH_EXPANDED - SIDEBAR_WIDTH_COLLAPSED)
        self.button_frame.pack_propagate(False)
        self.button_frame.pack(side=tk.LEFT, fill=tk.Y, expand=True, padx=0)
        self.button_frame.pack_forget()  # Скрыто изначально

        # Прокрутка
        self.scroll_canvas = tk.Canvas(self.button_frame, bg="#5A3A35", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.button_frame, orient="vertical", command=self.scroll_canvas.yview)
        self.scrollable_frame = tk.Frame(self.scroll_canvas, bg="#5A3A35")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))
        )

        self.scroll_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scroll_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # События
        self.canvas.bind("<Button-1>", self.toggle_expand)
        self.root.bind("<Button-3>", self.show_context_menu)

        # Меню
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Добавить ярлык", command=self.add_shortcut)
        self.context_menu.add_command(label="Слева", command=lambda: self.set_side("left"))
        self.context_menu.add_command(label="Справа", command=lambda: self.set_side("right"))
        self.context_menu.add_command(label="Выход", command=self.quit_app)

        # Иконка в трее
        self.icon = None
        if CONFIG["show_tray"]:
            self.init_tray_icon()

        # Ярлыки
        self.shortcuts = []
        self.buttons = []
        self.load_shortcuts()

    def update_position(self):
        x = 0 if SIDE == "left" else self.screen_width - SIDEBAR_WIDTH_COLLAPSED
        self.root.geometry(f"{SIDEBAR_WIDTH_COLLAPSED}x{self.screen_height - 40}+{x}+20")

    def draw_arrow(self):
        self.canvas.delete("all")
        w, h = SIDEBAR_WIDTH_COLLAPSED, self.screen_height - 40
        mid_h = h // 2

        if SIDE == "left":
            points = [w - 6, mid_h - 5, w - 6, mid_h + 5, w - 2, mid_h]
        else:
            points = [6, mid_h - 5, 6, mid_h + 5, 2, mid_h]

        self.canvas.create_polygon(points, fill="white", outline="")

    def toggle_expand(self, event=None):
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.button_frame.pack(side=tk.LEFT, fill=tk.Y)
            self.animate(True)
        else:
            self.animate(False)

    def animate(self, expand):
        if self.animation_running:
            return
        self.animation_running = True
        target = SIDEBAR_WIDTH_EXPANDED if expand else SIDEBAR_WIDTH_COLLAPSED
        self.animate_step(target)

    def animate_step(self, target):
        step = ANIMATION_STEP if self.current_width < target else -ANIMATION_STEP

        if abs(self.current_width - target) < ANIMATION_STEP:
            self.current_width = target
            if not self.is_expanded:
                self.button_frame.pack_forget()
            self.animation_running = False
        else:
            self.current_width += step

        x = 0 if SIDE == "left" else self.screen_width - self.current_width
        self.root.geometry(f"{self.current_width}x{self.screen_height - 40}+{x}+20")

        if abs(self.current_width - target) >= ANIMATION_STEP:
            self.root.after(ANIMATION_DELAY, self.animate_step, target)
        else:
            self.animation_running = False

    def show_context_menu(self, event):
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def set_side(self, side):
        global SIDE
        SIDE = side
        CONFIG["side"] = side
        self.save_config()
        self.update_position()
        self.draw_arrow()

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(CONFIG, f, ensure_ascii=False, indent=2)

    def load_shortcuts(self):
        if os.path.exists("shortcuts.json"):
            try:
                with open("shortcuts.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for path in data:
                        if os.path.exists(path):
                            self.add_shortcut_button(path)
                            self.shortcuts.append(path)
            except Exception as e:
                print(f"Ошибка загрузки ярлыков: {e}")

    def add_shortcut(self):
        path = filedialog.askopenfilename(
            title="Выберите .exe или .lnk",
            filetypes=[("Executables", "*.exe"), ("Shortcuts", "*.lnk"), ("All", "*.*")]
        )
        if path and path not in self.shortcuts:
            self.shortcuts.append(path)
            self.add_shortcut_button(path)
            self.save_shortcuts()

    def add_shortcut_button(self, path):
        frame = tk.Frame(self.scrollable_frame, bg="#5A3A35")
        frame.pack(fill=tk.X, pady=2)

        name = os.path.splitext(os.path.basename(path))[0]
        btn = tk.Button(
            frame,
            text=name,
            fg="white",
            bg="#6C4A42",
            activebackground="#8B5A4A",
            activeforeground="white",
            relief="flat",
            font=("Segoe UI", 9),
            command=lambda: self.launch(path)
        )
        btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 2))
        btn.bind("<Enter>", lambda e: btn.config(bg="#7A554D"))
        btn.bind("<Leave>", lambda e: btn.config(bg="#6C4A42"))

        remove_btn = tk.Button(
            frame,
            text="×",
            bg="#A00",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            width=2,
            relief="flat",
            command=lambda: self.remove_shortcut(path, frame)
        )
        remove_btn.pack(side=tk.RIGHT, padx=2)
        remove_btn.bind("<Enter>", lambda e: remove_btn.config(bg="#C00"))

        self.buttons.append((frame, path))

    def launch(self, path):
        try:
            if path.endswith(".lnk"):
                subprocess.run(["powershell", "-Command", f"Start-Process '{path}'"], shell=True)
            else:
                os.startfile(path)
        except Exception as e:
            print(f"Ошибка: {e}")

    def remove_shortcut(self, path, frame):
        if path in self.shortcuts:
            self.shortcuts.remove(path)
        frame.destroy()
        self.buttons = [(f, p) for f, p in self.buttons if p != path]
        self.save_shortcuts()

    def save_shortcuts(self):
        with open("shortcuts.json", "w", encoding="utf-8") as f:
            json.dump(self.shortcuts, f, ensure_ascii=False, indent=2)

    def init_tray_icon(self):
        image = self.create_tray_icon()
        menu = pystray.Menu(
            item('Показать', self.tray_show),
            item('Добавить ярлык', self.tray_add),
            item('Слева', lambda: self.set_side("left")),
            item('Справа', lambda: self.set_side("right")),
            item('Выход', self.tray_exit)
        )
        self.icon = pystray.Icon("Sidebar", image, "Сайдбар-лаунчер", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def create_tray_icon(self):
        width, height = 64, 64
        color1 = (75, 46, 42)   # Коричневый
        color2 = (255, 255, 255)  # Белый
        image = Image.new('RGB', (width, height), color1)
        draw = ImageDraw.Draw(image)
        # Простая стрелка
        if SIDE == "right":
            draw.polygon([
                (width // 4, height // 4),
                (width // 4, 3 * height // 4),
                (3 * width // 4, height // 2)
            ], fill=color2)
        else:
            draw.polygon([
                (3 * width // 4, height // 4),
                (3 * width // 4, 3 * height // 4),
                (width // 4, height // 2)
            ], fill=color2)
        return image

    def tray_show(self, icon, item):
        self.root.after(0, self.root.deiconify)

    def tray_add(self, icon, item):
        self.root.after(0, self.add_shortcut)

    def tray_exit(self, icon, item):
        self.root.after(0, self.quit_app)

    def quit_app(self):
        if self.icon:
            self.icon.stop()
        self.root.quit()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = SidebarLauncher()
    app.run()