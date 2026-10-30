"""UI helper components, layout managers, and styling utilities."""

import tkinter as tk
from tkinter import ttk
from config import BG, SURFACE, SURFACE_2, BORDER, FG, MUTED, ACCENT, ACCENT_HI, DANGER, DANGER_BG, FONT, F_BODY, F_SMALL


def center_window(win, width, height):
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - width) // 2
    y = (sh - height) // 2
    win.geometry(f"{width}x{height}+{x}+{y}")


def apply_theme(root):
    style = ttk.Style(root)
    style.theme_use("clam")
    
    # Configure global dark theme colors for ttk widgets
    style.configure(".", background=BG, foreground=FG, font=(FONT, 10))
    style.configure("TCombobox", fieldbackground=SURFACE, background=SURFACE, foreground=FG, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
    style.map("TCombobox", fieldbackground=[("readonly", SURFACE)], selectbackground=[("readonly", ACCENT)])
    
    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=FG, bordercolor=BORDER, rowheight=26)
    style.configure("Treeview.Heading", background=SURFACE_2, foreground=FG, font=(FONT, 9, "bold"))
    style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", FG)])


def make_button(parent, text, command, accent=False, anchor="w", width=None):
    bg_color = ACCENT if accent else SURFACE_2
    fg_color = FG if accent else FG
    hover_color = ACCENT_HI if accent else SURFACE

    btn = tk.Button(parent, text=text, command=command, bg=bg_color, fg=fg_color,
                    activebackground=hover_color, activeforeground=fg_color,
                    relief="flat", font=(FONT, 10, "bold"), anchor=anchor, padx=14, pady=8, cursor="hand2")
    if width:
        btn.configure(width=width)

    # Smooth hover effect
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover_color))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg_color))
    return btn


def make_small_button(parent, text, command, danger=False):
    bg_color = DANGER_BG if danger else SURFACE_2
    fg_color = DANGER if danger else FG
    hover_color = "#3a2323" if danger else SURFACE

    btn = tk.Button(parent, text=text, command=command, bg=bg_color, fg=fg_color,
                    activebackground=hover_color, activeforeground=fg_color,
                    relief="flat", font=(FONT, 9), anchor="w", padx=10, pady=5, cursor="hand2")

    btn.bind("<Enter>", lambda e: btn.configure(bg=hover_color))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg_color))
    return btn


def card_frame(parent, title, bg=SURFACE, title_fg=FG, row=0, column=0, padx=4, pady=0):
    # Outer wrapper to create physical gap between cards
    outer = tk.Frame(parent, bg=parent.cget("bg"))
    outer.grid(row=row, column=column, sticky="nsew", padx=padx, pady=pady)
    outer.columnconfigure(0, weight=1)

    # Inner card body
    frame = tk.Frame(outer, bg=bg, highlightbackground=BORDER, highlightthickness=1, padx=12, pady=12)
    frame.pack(fill="both", expand=True, padx=2, pady=2)

    return frame


def attach_autofit(tree):
    def autofit(event=None):
        for col in tree["columns"]:
            max_w = max(
                (len(str(tree.item(item, "values")[tree["columns"].index(col)])) for item in tree.get_children()),
                default=len(str(col))
            )
            tree.column(col, width=max(max_w * 9 + 20, 80))
    tree.bind("<<TreeviewOpen>>", autofit)
    return autofit