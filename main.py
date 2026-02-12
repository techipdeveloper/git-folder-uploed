"""
Git Folder Uploader v2.1 - Techip Developers
=============================================
Professional GUI to upload entire folders to GitHub / GitLab.
Features animated step indicators, progress bar, pulsing button,
hover effects, and a polished dark UI.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import sys
import shutil
import time
import math

# ---------------------------------------------------------------------------
# PyInstaller resource helper
# ---------------------------------------------------------------------------
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
BG_DARK       = "#0f0f1a"
BG_MID        = "#151528"
BG_CARD       = "#1a1a35"
BG_CARD_HOVER = "#1f1f40"
BG_INPUT      = "#12122a"
BG_INPUT_FOCUS= "#1a1a3a"
BORDER_CARD   = "#2a2a50"
BORDER_FOCUS  = "#4f46e5"

ACCENT_BLUE   = "#3b82f6"
ACCENT_CYAN   = "#06b6d4"
ACCENT_PURPLE = "#a855f7"
ACCENT_INDIGO = "#6366f1"

SUCCESS       = "#22c55e"
SUCCESS_DIM   = "#166534"
ERROR         = "#ef4444"
ERROR_DIM     = "#7f1d1d"
WARNING       = "#f59e0b"
WARNING_DIM   = "#78350f"

TEXT_PRIMARY   = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED     = "#475569"

GITHUB_CLR    = "#238636"
GITHUB_HOVER  = "#2ea043"
GITLAB_CLR    = "#fc6d26"
GITLAB_HOVER  = "#e65a15"

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# Spinner frames
SPINNER = ["   ", ".  ", ".. ", "..."]


# ---------------------------------------------------------------------------
# Animated Progress Bar (canvas-based)
# ---------------------------------------------------------------------------
class AnimatedProgressBar(tk.Canvas):
    """A smooth animated progress bar with gradient fill."""

    def __init__(self, parent, height=6, **kw):
        super().__init__(parent, height=height, highlightthickness=0,
                         bg=BG_DARK, **kw)
        self._progress = 0.0        # 0..1
        self._target = 0.0
        self._animating = False
        self._pulse_mode = False
        self._pulse_pos = 0.0
        self.bind("<Configure>", lambda _: self._draw())

    def set_progress(self, value):
        self._target = max(0.0, min(1.0, value))
        self._pulse_mode = False
        if not self._animating:
            self._animating = True
            self._animate()

    def start_pulse(self):
        self._pulse_mode = True
        self._pulse_pos = 0.0
        if not self._animating:
            self._animating = True
            self._animate_pulse()

    def stop(self):
        self._pulse_mode = False
        self._animating = False
        self._progress = 0.0
        self._target = 0.0
        self._draw()

    def complete(self):
        self._pulse_mode = False
        self._target = 1.0
        if not self._animating:
            self._animating = True
            self._animate()

    def _animate(self):
        if self._pulse_mode:
            return
        diff = self._target - self._progress
        if abs(diff) < 0.005:
            self._progress = self._target
            self._animating = False
            self._draw()
            return
        self._progress += diff * 0.15
        self._draw()
        self.after(16, self._animate)

    def _animate_pulse(self):
        if not self._pulse_mode:
            self._animating = False
            self._draw()
            return
        self._pulse_pos = (self._pulse_pos + 0.02) % 1.0
        self._draw_pulse()
        self.after(16, self._animate_pulse)

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2:
            return
        # Background track
        self.create_rectangle(0, 0, w, h, fill="#1e1e3a", outline="")
        # Filled portion
        fill_w = int(w * self._progress)
        if fill_w > 0:
            # Gradient effect via multiple thin rectangles
            steps = min(fill_w, 30)
            for i in range(steps):
                x = int(fill_w * i / steps)
                x2 = int(fill_w * (i + 1) / steps)
                r = int(59 + (34 - 59) * i / steps)
                g = int(130 + (211 - 130) * i / steps)
                b = int(246 + (212 - 246) * i / steps)
                self.create_rectangle(x, 0, x2, h,
                                      fill=f"#{r:02x}{g:02x}{b:02x}", outline="")

    def _draw_pulse(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2:
            return
        self.create_rectangle(0, 0, w, h, fill="#1e1e3a", outline="")
        # Moving highlight
        pulse_w = int(w * 0.3)
        center = int(w * self._pulse_pos)
        x1 = center - pulse_w // 2
        x2 = center + pulse_w // 2
        for i in range(max(0, x1), min(w, x2)):
            dist = abs(i - center) / (pulse_w / 2)
            alpha = max(0, 1 - dist)
            r = int(30 + 29 * alpha)
            g = int(30 + 100 * alpha)
            b = int(58 + 188 * alpha)
            self.create_rectangle(i, 0, i + 1, h,
                                  fill=f"#{r:02x}{g:02x}{b:02x}", outline="")


# ---------------------------------------------------------------------------
# Step Indicator Widget
# ---------------------------------------------------------------------------
class StepIndicator(tk.Frame):
    """Circular status indicator: pending / running / done / error."""

    STATES = {
        "pending":  ("○", TEXT_MUTED),
        "running":  ("●", ACCENT_BLUE),
        "done":     ("✓", SUCCESS),
        "error":    ("✗", ERROR),
    }

    def __init__(self, parent, number, title, desc, **kw):
        super().__init__(parent, bg=BG_CARD, **kw)
        self._state = "pending"
        self._pulse_after = None

        # Row layout
        top = tk.Frame(self, bg=BG_CARD)
        top.pack(fill="x", pady=(0, 2))

        self._icon = tk.Label(top, text="○", font=("Segoe UI", 14),
                              fg=TEXT_MUTED, bg=BG_CARD, width=2)
        self._icon.pack(side="left", padx=(0, 6))

        self._num = tk.Label(top, text=f"STEP {number}",
                             font=("Segoe UI", 8, "bold"),
                             fg=TEXT_MUTED, bg=BG_CARD)
        self._num.pack(side="left", padx=(0, 8))

        self._title = tk.Label(top, text=title,
                               font=("Segoe UI", 11, "bold"),
                               fg=TEXT_PRIMARY, bg=BG_CARD)
        self._title.pack(side="left")

        self._status_lbl = tk.Label(top, text="",
                                    font=("Segoe UI", 9),
                                    fg=TEXT_MUTED, bg=BG_CARD)
        self._status_lbl.pack(side="right", padx=(8, 0))

        if desc:
            self._desc = tk.Label(self, text=desc,
                                  font=("Segoe UI", 9), fg=TEXT_SECONDARY,
                                  bg=BG_CARD, wraplength=620, justify="left")
            self._desc.pack(anchor="w", padx=(38, 0))

    def set_state(self, state, status_text=""):
        self._state = state
        symbol, colour = self.STATES.get(state, ("○", TEXT_MUTED))
        self._icon.configure(text=symbol, fg=colour)
        self._status_lbl.configure(text=status_text, fg=colour)
        if self._pulse_after:
            self.after_cancel(self._pulse_after)
            self._pulse_after = None
        if state == "running":
            self._start_pulse()

    def _start_pulse(self):
        """Animate the running icon between bright and dim."""
        colours = ["#3b82f6", "#60a5fa", "#93c5fd", "#60a5fa"]
        idx = [0]
        def _tick():
            if self._state != "running":
                return
            self._icon.configure(fg=colours[idx[0] % len(colours)])
            idx[0] += 1
            self._pulse_after = self.after(350, _tick)
        _tick()


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------
class GitFolderUploader:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Git Folder Uploader  |  Techip")
        self.root.geometry("820x1020")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(True, True)
        self.root.minsize(760, 950)

        # Variables
        self.platform     = tk.StringVar(value="github")
        self.repo_url     = tk.StringVar()
        self.folder_path  = tk.StringVar()
        self.commit_msg   = tk.StringVar(value="Initial commit of local folder contents")
        self.branch_name  = tk.StringVar(value="main")
        self.git_user     = tk.StringVar()
        self.git_email    = tk.StringVar()
        self.git_installed = False
        self.is_running    = False
        self._btn_pulse_id = None

        self._load_icon()
        self._build_ui()

        # Fade-in animation
        self.root.attributes("-alpha", 0.0)
        self._fade_in(0.0)

        self.root.after(800, self._check_git_installation)

    # -----------------------------------------------------------------------
    @property
    def _plat(self):
        return "GitHub" if self.platform.get() == "github" else "GitLab"

    # -----------------------------------------------------------------------
    # Fade in
    # -----------------------------------------------------------------------
    def _fade_in(self, alpha):
        if alpha >= 1.0:
            self.root.attributes("-alpha", 1.0)
            return
        self.root.attributes("-alpha", alpha)
        self.root.after(20, lambda: self._fade_in(alpha + 0.05))

    # -----------------------------------------------------------------------
    # Icon
    # -----------------------------------------------------------------------
    def _load_icon(self):
        try:
            from PIL import Image, ImageTk
            path = resource_path("logo.png")
            if os.path.exists(path):
                img = Image.open(path).resize((32, 32), Image.LANCZOS)
                self._icon_ref = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, self._icon_ref)
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Build UI
    # -----------------------------------------------------------------------
    def _build_ui(self):
        # Scrollable area
        canvas = tk.Canvas(self.root, bg=BG_DARK, highlightthickness=0)
        vsb = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        self._frame = tk.Frame(canvas, bg=BG_DARK)
        self._frame.bind("<Configure>",
                         lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self._frame, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        pad = 28  # consistent side padding

        # ============ HEADER ============
        hdr = tk.Frame(self._frame, bg=BG_DARK, pady=16)
        hdr.pack(fill="x", padx=pad)

        try:
            from PIL import Image, ImageTk
            lp = resource_path("logo.png")
            if os.path.exists(lp):
                img = Image.open(lp).resize((64, 64), Image.LANCZOS)
                self._logo_ref = ImageTk.PhotoImage(img)
                tk.Label(hdr, image=self._logo_ref, bg=BG_DARK).pack(side="left", padx=(0, 18))
        except Exception:
            pass

        title_box = tk.Frame(hdr, bg=BG_DARK)
        title_box.pack(side="left", fill="x")
        tk.Label(title_box, text="Git Folder Uploader",
                 font=("Segoe UI", 24, "bold"), fg=TEXT_PRIMARY,
                 bg=BG_DARK).pack(anchor="w")
        tk.Label(title_box, text="Upload entire folders to GitHub or GitLab with one click",
                 font=("Segoe UI", 11), fg=TEXT_SECONDARY,
                 bg=BG_DARK).pack(anchor="w", pady=(2, 0))

        # Gradient separator
        sep_canvas = tk.Canvas(self._frame, height=3, bg=BG_DARK, highlightthickness=0)
        sep_canvas.pack(fill="x", padx=pad, pady=(0, 12))
        sep_canvas.bind("<Configure>", lambda e: self._draw_gradient_line(sep_canvas))

        # ============ PROGRESS BAR ============
        self._progress = AnimatedProgressBar(self._frame, height=4)
        self._progress.pack(fill="x", padx=pad, pady=(0, 12))

        # ============ STEP 1 : Git Check ============
        card1, inner1 = self._card(pad)
        self._step1 = StepIndicator(inner1, 1, "Git Installation Check",
                                    "Checking if Git is installed on your computer.")
        self._step1.pack(fill="x")

        self._git_lbl = tk.Label(inner1, text="   Checking...",
                                 font=("Segoe UI", 10), fg=WARNING, bg=BG_CARD)
        self._git_lbl.pack(anchor="w", padx=38, pady=(4, 0))

        self._install_btn = tk.Button(inner1, text="  Install Git  ",
                                      font=("Segoe UI", 10, "bold"),
                                      bg=ACCENT_PURPLE, fg="white",
                                      activebackground="#9333ea",
                                      relief="flat", padx=14, pady=5,
                                      cursor="hand2", command=self._install_git)
        self._install_btn.pack(anchor="w", padx=38, pady=(6, 0))
        self._install_btn.pack_forget()

        # ============ STEP 2 : Platform ============
        card2, inner2 = self._card(pad)
        self._step2 = StepIndicator(inner2, 2, "Choose Platform",
                                    "Select where you want to upload your folder.")
        self._step2.pack(fill="x")
        self._step2.set_state("done", "Ready")

        radio_frame = tk.Frame(inner2, bg=BG_CARD)
        radio_frame.pack(anchor="w", padx=38, pady=(8, 0))

        self._gh_btn = tk.Button(radio_frame, text="  GitHub  ",
                                 font=("Segoe UI", 11, "bold"),
                                 bg=GITHUB_CLR, fg="white", relief="flat",
                                 padx=20, pady=6, cursor="hand2",
                                 command=lambda: self._set_platform("github"))
        self._gh_btn.pack(side="left", padx=(0, 12))
        self._gl_btn = tk.Button(radio_frame, text="  GitLab  ",
                                 font=("Segoe UI", 11, "bold"),
                                 bg=BG_INPUT, fg=TEXT_MUTED, relief="flat",
                                 padx=20, pady=6, cursor="hand2",
                                 command=lambda: self._set_platform("gitlab"))
        self._gl_btn.pack(side="left")

        # ============ STEP 3 : URL ============
        card3, inner3 = self._card(pad)
        self._step3 = StepIndicator(inner3, 3, "Repository URL", "")
        self._step3.pack(fill="x")
        self._url_desc = tk.Label(inner3, text="", font=("Segoe UI", 9),
                                  fg=TEXT_SECONDARY, bg=BG_CARD,
                                  wraplength=660, justify="left")
        self._url_desc.pack(anchor="w", padx=38, pady=(2, 4))
        self._make_entry(inner3, self.repo_url, "https://github.com/user/repo.git")

        # ============ STEP 4 : Folder ============
        card4, inner4 = self._card(pad)
        self._step4 = StepIndicator(inner4, 4, "Select Folder to Upload",
                                    "Choose the local folder whose contents will be pushed.")
        self._step4.pack(fill="x")

        folder_row = tk.Frame(inner4, bg=BG_CARD)
        folder_row.pack(fill="x", padx=38, pady=(8, 0))
        fe = tk.Entry(folder_row, textvariable=self.folder_path,
                      font=("Consolas", 11), bg=BG_INPUT, fg=TEXT_PRIMARY,
                      insertbackground=TEXT_PRIMARY, relief="flat",
                      highlightthickness=1, highlightbackground=BORDER_CARD,
                      highlightcolor=BORDER_FOCUS)
        fe.pack(side="left", fill="x", expand=True, ipady=8, ipadx=10)
        browse_btn = tk.Button(folder_row, text="  Browse  ",
                               font=("Segoe UI", 10, "bold"),
                               bg=ACCENT_CYAN, fg="white",
                               activebackground="#0891b2",
                               relief="flat", padx=14, pady=6,
                               cursor="hand2", command=self._select_folder)
        browse_btn.pack(side="right", padx=(10, 0))
        self._add_hover(browse_btn, ACCENT_CYAN, "#0891b2")

        # ============ STEP 5 : Commit message ============
        card5, inner5 = self._card(pad)
        self._step5 = StepIndicator(inner5, 5, "Commit Message",
                                    "Describe what you are uploading. Keep the default or customize.")
        self._step5.pack(fill="x")
        self._make_entry(inner5, self.commit_msg)

        # ============ STEP 6 : Branch ============
        card6, inner6 = self._card(pad)
        self._step6 = StepIndicator(inner6, 6, "Branch Name",
                                    "The remote branch to push to (usually 'main' or 'master').")
        self._step6.pack(fill="x")
        self._make_entry(inner6, self.branch_name)

        # ============ STEP 7 : Identity ============
        card7, inner7 = self._card(pad)
        self._step7 = StepIndicator(inner7, 7, "Git Identity (optional)",
                                    "Fill in if Git complains about missing name/email.")
        self._step7.pack(fill="x")
        self._make_entry(inner7, self.git_user, "Your Name")
        self._make_entry(inner7, self.git_email, "you@example.com")

        # ============ PUSH BUTTON ============
        btn_frame = tk.Frame(self._frame, bg=BG_DARK, pady=14)
        btn_frame.pack(fill="x", padx=pad)

        self._push_btn = tk.Button(
            btn_frame, text="     UPLOAD TO GITHUB     ",
            font=("Segoe UI", 16, "bold"), bg=GITHUB_CLR, fg="white",
            activebackground=GITHUB_HOVER, activeforeground="white",
            relief="flat", pady=16, cursor="hand2", bd=0,
            command=self._start_push)
        self._push_btn.pack(fill="x")
        self._add_hover(self._push_btn, GITHUB_CLR, GITHUB_HOVER)

        warn_frame = tk.Frame(btn_frame, bg=BG_DARK)
        warn_frame.pack(pady=(8, 0))
        tk.Label(warn_frame, text="\u26A0", font=("Segoe UI", 10),
                 fg=WARNING, bg=BG_DARK).pack(side="left", padx=(0, 6))
        tk.Label(warn_frame, text="This will OVERWRITE the remote repository contents!",
                 font=("Segoe UI", 9, "italic"), fg=ERROR,
                 bg=BG_DARK).pack(side="left")

        # ============ LOG ============
        log_card, log_inner = self._card(pad)
        log_header = tk.Frame(log_inner, bg=BG_CARD)
        log_header.pack(fill="x", pady=(0, 6))
        tk.Label(log_header, text="\u2630", font=("Segoe UI", 12),
                 fg=ACCENT_INDIGO, bg=BG_CARD).pack(side="left", padx=(0, 8))
        tk.Label(log_header, text="Output Log",
                 font=("Segoe UI", 12, "bold"), fg=TEXT_PRIMARY,
                 bg=BG_CARD).pack(side="left")
        self._spinner_lbl = tk.Label(log_header, text="",
                                     font=("Consolas", 11, "bold"),
                                     fg=ACCENT_CYAN, bg=BG_CARD)
        self._spinner_lbl.pack(side="right")

        self._log = tk.Text(log_inner, height=14, font=("Consolas", 10),
                            bg="#08081a", fg=TEXT_PRIMARY,
                            insertbackground=TEXT_PRIMARY, relief="flat",
                            wrap="word", state="disabled", padx=12, pady=8,
                            highlightthickness=1,
                            highlightbackground="#1a1a3a",
                            highlightcolor="#1a1a3a")
        self._log.pack(fill="both", expand=True, pady=(0, 4))

        for tag, colour, bold in [
            ("info", ACCENT_CYAN, False), ("ok", SUCCESS, False),
            ("err", ERROR, False), ("warn", WARNING, False),
            ("step", ACCENT_PURPLE, True), ("cmd", ACCENT_INDIGO, False),
            ("banner", ACCENT_BLUE, True)]:
            self._log.tag_configure(
                tag, foreground=colour,
                font=("Consolas", 10, "bold") if bold else ("Consolas", 10))

        # ============ FOOTER ============
        ft = tk.Frame(self._frame, bg=BG_DARK, pady=16)
        ft.pack(fill="x", padx=pad)

        # Gradient separator
        sep2 = tk.Canvas(ft, height=1, bg=BG_DARK, highlightthickness=0)
        sep2.pack(fill="x", pady=(0, 12))
        sep2.bind("<Configure>", lambda e: self._draw_gradient_line(sep2))

        footer_inner = tk.Frame(ft, bg=BG_DARK)
        footer_inner.pack()
        try:
            from PIL import Image, ImageTk
            lp = resource_path("logo.png")
            if os.path.exists(lp):
                small = Image.open(lp).resize((24, 24), Image.LANCZOS)
                self._flogo = ImageTk.PhotoImage(small)
                tk.Label(footer_inner, image=self._flogo, bg=BG_DARK).pack(side="left", padx=(0, 8))
        except Exception:
            pass

        tk.Label(footer_inner, text="Developed by Techip Developers",
                 font=("Segoe UI", 10, "bold"), fg=TEXT_SECONDARY,
                 bg=BG_DARK).pack(side="left")
        tk.Label(ft, text="v2.1.0",
                 font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_DARK).pack(pady=(4, 0))

        # Initialise platform UI
        self._set_platform("github")

    # -----------------------------------------------------------------------
    # UI helpers
    # -----------------------------------------------------------------------
    def _draw_gradient_line(self, canvas):
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 2:
            return
        for i in range(w):
            t = i / max(w - 1, 1)
            r = int(59 * (1 - t) + 168 * t)
            g = int(130 * (1 - t) + 85 * t)
            b = int(246 * (1 - t) + 247 * t)
            canvas.create_rectangle(i, 0, i + 1, h,
                                    fill=f"#{r:02x}{g:02x}{b:02x}", outline="")

    def _card(self, pad):
        """Create a card container with hover highlight border."""
        outer = tk.Frame(self._frame, bg=BORDER_CARD,
                         highlightthickness=0, bd=1, relief="flat")
        outer.pack(fill="x", padx=pad, pady=5)
        inner = tk.Frame(outer, bg=BG_CARD, padx=16, pady=12)
        inner.pack(fill="x")

        def _enter(_):
            outer.configure(bg=ACCENT_INDIGO)
        def _leave(_):
            outer.configure(bg=BORDER_CARD)
        outer.bind("<Enter>", _enter)
        outer.bind("<Leave>", _leave)

        return outer, inner

    def _make_entry(self, parent, var, placeholder=""):
        frame = tk.Frame(parent, bg=BG_CARD)
        frame.pack(fill="x", padx=38, pady=(6, 0))
        e = tk.Entry(frame, textvariable=var,
                     font=("Consolas", 11), bg=BG_INPUT, fg=TEXT_PRIMARY,
                     insertbackground=TEXT_PRIMARY, relief="flat",
                     highlightthickness=1, highlightbackground=BORDER_CARD,
                     highlightcolor=BORDER_FOCUS)
        e.pack(fill="x", ipady=8, ipadx=10)
        if placeholder and not var.get():
            e.insert(0, placeholder)
            e.configure(fg=TEXT_MUTED)

            def _fi(_):
                if e.get() == placeholder:
                    e.delete(0, "end")
                    e.configure(fg=TEXT_PRIMARY)
            def _fo(_):
                if not e.get():
                    e.insert(0, placeholder)
                    e.configure(fg=TEXT_MUTED)
            e.bind("<FocusIn>", _fi)
            e.bind("<FocusOut>", _fo)
        return e

    def _add_hover(self, btn, normal, hover):
        btn.bind("<Enter>", lambda _: btn.configure(bg=hover))
        btn.bind("<Leave>", lambda _: btn.configure(bg=normal))

    # -----------------------------------------------------------------------
    # Platform toggle
    # -----------------------------------------------------------------------
    def _set_platform(self, plat_id):
        self.platform.set(plat_id)
        plat = self._plat
        if plat == "GitHub":
            self._gh_btn.configure(bg=GITHUB_CLR, fg="white")
            self._gl_btn.configure(bg=BG_INPUT, fg=TEXT_MUTED)
            self._url_desc.configure(
                text="Paste the HTTPS URL of your GitHub repository.\n"
                     "Example: https://github.com/username/my-repo.git")
            self._push_btn.configure(
                text="     UPLOAD TO GITHUB     ",
                bg=GITHUB_CLR, activebackground=GITHUB_HOVER)
            self._add_hover(self._push_btn, GITHUB_CLR, GITHUB_HOVER)
        else:
            self._gl_btn.configure(bg=GITLAB_CLR, fg="white")
            self._gh_btn.configure(bg=BG_INPUT, fg=TEXT_MUTED)
            self._url_desc.configure(
                text="Paste the HTTPS URL of your GitLab repository.\n"
                     "Example: https://gitlab.com/username/my-repo.git")
            self._push_btn.configure(
                text="     UPLOAD TO GITLAB     ",
                bg=GITLAB_CLR, activebackground=GITLAB_HOVER)
            self._add_hover(self._push_btn, GITLAB_CLR, GITLAB_HOVER)

    # -----------------------------------------------------------------------
    # Button pulse animation
    # -----------------------------------------------------------------------
    def _start_btn_pulse(self):
        colours = ["#475569", "#525e6e", "#5e6b7a", "#525e6e"]
        idx = [0]
        def _tick():
            if not self.is_running:
                return
            self._push_btn.configure(bg=colours[idx[0] % len(colours)])
            idx[0] += 1
            self._btn_pulse_id = self.root.after(400, _tick)
        _tick()

    def _stop_btn_pulse(self):
        if self._btn_pulse_id:
            self.root.after_cancel(self._btn_pulse_id)
            self._btn_pulse_id = None

    # -----------------------------------------------------------------------
    # Spinner animation
    # -----------------------------------------------------------------------
    def _start_spinner(self):
        idx = [0]
        def _tick():
            if not self.is_running:
                self._spinner_lbl.configure(text="")
                return
            self._spinner_lbl.configure(text=SPINNER[idx[0] % len(SPINNER)])
            idx[0] += 1
            self.root.after(500, _tick)
        _tick()

    # -----------------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------------
    def _log_msg(self, text, tag="info"):
        def _do():
            self._log.configure(state="normal")
            self._log.insert("end", text + "\n", tag)
            self._log.see("end")
            self._log.configure(state="disabled")
        if threading.current_thread() is threading.main_thread():
            _do()
        else:
            self.root.after(0, _do)

    # -----------------------------------------------------------------------
    # Step 1 - Git check / install
    # -----------------------------------------------------------------------
    def _check_git_installation(self):
        self._step1.set_state("running", "Checking...")
        try:
            r = subprocess.run(["git", "--version"],
                               capture_output=True, text=True, timeout=15,
                               creationflags=CREATE_NO_WINDOW)
            if r.returncode == 0:
                ver = r.stdout.strip()
                self._git_lbl.configure(text=f"   {ver}", fg=SUCCESS)
                self.git_installed = True
                self._install_btn.pack_forget()
                self._step1.set_state("done", "Installed")
                self._log_msg(f"Git detected: {ver}", "ok")
                return
        except Exception:
            pass
        self._git_lbl.configure(
            text="   Git is NOT installed.", fg=ERROR)
        self.git_installed = False
        self._install_btn.pack(anchor="w", padx=38, pady=(6, 0))
        self._step1.set_state("error", "Not found")
        self._log_msg("Git is not installed on this computer.", "err")
        self._log_msg("Click 'Install Git' or download from https://git-scm.com/download/win", "warn")

    def _install_git(self):
        self._install_btn.configure(state="disabled", text="  Installing...  ")
        self._step1.set_state("running", "Installing...")
        self._log_msg("\n--- Installing Git via winget ---", "step")

        def _worker():
            try:
                proc = subprocess.Popen(
                    ["winget", "install", "--id", "Git.Git", "-e",
                     "--source", "winget",
                     "--accept-package-agreements",
                     "--accept-source-agreements"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, creationflags=CREATE_NO_WINDOW)
                out, err = proc.communicate(timeout=600)
                for line in (out or "").strip().splitlines():
                    if line.strip():
                        self._log_msg(f"  {line}", "info")
                if proc.returncode == 0:
                    self._log_msg("Git installed successfully!", "ok")
                    self._log_msg("Restart this app for Git to be recognized.", "warn")
                    self.root.after(0, lambda: self._git_lbl.configure(
                        text="   Installed! Restart app.", fg=SUCCESS))
                    self.root.after(0, lambda: self._step1.set_state("done", "Installed"))
                    self.git_installed = True
                else:
                    self._log_msg("Installation may have failed.", "err")
                    self.root.after(0, lambda: self._step1.set_state("error", "Failed"))
            except FileNotFoundError:
                self._log_msg("winget not available. Install Git manually:", "err")
                self._log_msg("  https://git-scm.com/download/win", "warn")
                self.root.after(0, lambda: self._step1.set_state("error", "Manual install needed"))
            except Exception as exc:
                self._log_msg(f"Error: {exc}", "err")
                self.root.after(0, lambda: self._step1.set_state("error", "Error"))
            finally:
                self.root.after(0, lambda: self._install_btn.configure(
                    state="normal", text="  Install Git  "))

        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # Folder selection
    # -----------------------------------------------------------------------
    def _select_folder(self):
        path = filedialog.askdirectory(title="Select Folder to Upload")
        if path:
            self.folder_path.set(path)
            self._step4.set_state("done", "Selected")
            self._log_msg(f"Selected folder: {path}", "info")

    # -----------------------------------------------------------------------
    # Command runner
    # -----------------------------------------------------------------------
    def _run(self, cmd, cwd):
        self._log_msg(f"  > {' '.join(cmd)}", "cmd")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               cwd=cwd, timeout=180,
                               creationflags=CREATE_NO_WINDOW)
            for ln in (r.stdout or "").strip().splitlines():
                self._log_msg(f"    {ln}", "info")
            for ln in (r.stderr or "").strip().splitlines():
                tag = "warn" if r.returncode == 0 else "err"
                self._log_msg(f"    {ln}", tag)
            return r.returncode == 0, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            self._log_msg("    Command timed out!", "err")
            return False, "", "timeout"
        except Exception as exc:
            self._log_msg(f"    Error: {exc}", "err")
            return False, "", str(exc)

    # -----------------------------------------------------------------------
    # Push flow
    # -----------------------------------------------------------------------
    def _set_step_indicator(self, indicator, state, text=""):
        self.root.after(0, lambda: indicator.set_state(state, text))

    def _start_push(self):
        plat = self._plat
        if self.is_running:
            messagebox.showwarning("Busy", "A push is already in progress!")
            return
        if not self.git_installed:
            messagebox.showerror("Git Required", "Git must be installed first (Step 1).")
            return
        url = self.repo_url.get().strip()
        if not url:
            messagebox.showerror("Missing URL", f"Enter your {plat} repository URL (Step 3).")
            return
        folder = self.folder_path.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Missing Folder", "Select a valid folder (Step 4).")
            return
        commit = self.commit_msg.get().strip()
        if not commit:
            messagebox.showerror("Missing Message", "Enter a commit message (Step 5).")
            return
        branch = self.branch_name.get().strip()
        if not branch:
            messagebox.showerror("Missing Branch", "Enter a branch name (Step 6).")
            return

        if not messagebox.askyesno(
                "Confirm Force Push",
                f"Platform: {plat}\n\n"
                f"OVERWRITE all contents in:\n{url}\n\n"
                f"With files from:\n{folder}\n\n"
                f"Branch: {branch}\n\nContinue?"):
            return

        self.is_running = True
        self._push_btn.configure(state="disabled", text="     UPLOADING...     ")
        self._start_btn_pulse()
        self._start_spinner()
        self._progress.start_pulse()
        threading.Thread(target=self._do_push, daemon=True).start()

    def _reset_ui_after_push(self, plat):
        btn_clr = GITHUB_CLR if plat == "GitHub" else GITLAB_CLR
        hover = GITHUB_HOVER if plat == "GitHub" else GITLAB_HOVER
        self.is_running = False
        self._stop_btn_pulse()
        self._progress.stop()

        def _do():
            self._push_btn.configure(
                state="normal",
                text=f"     UPLOAD TO {plat.upper()}     ",
                bg=btn_clr)
            self._add_hover(self._push_btn, btn_clr, hover)
        self.root.after(0, _do)

    def _do_push(self):
        plat   = self._plat
        url    = self.repo_url.get().strip()
        folder = self.folder_path.get().strip()
        commit = self.commit_msg.get().strip()
        branch = self.branch_name.get().strip()
        user   = self.git_user.get().strip()
        email  = self.git_email.get().strip()
        if user in ("Your Name", ""):
            user = ""
        if email in ("you@example.com", ""):
            email = ""

        steps = [self._step3, self._step4, self._step5, self._step6, self._step7]

        try:
            self._log_msg("")
            self._log_msg("  ╔══════════════════════════════════════════════════╗", "banner")
            self._log_msg(f"  ║     STARTING {plat.upper()} UPLOAD PROCESS              ║", "banner")
            self._log_msg("  ╚══════════════════════════════════════════════════╝", "banner")

            # -- 1 Navigate ----
            self._set_step_indicator(self._step3, "running", "Navigating...")
            self._log_msg(f"\n[Step 1/6] Navigating to folder...", "step")
            self._log_msg(f"  {folder}", "info")
            if not os.path.isdir(folder):
                self._log_msg("  Folder does not exist!", "err")
                self._set_step_indicator(self._step4, "error", "Not found")
                return
            self.root.after(0, lambda: self._progress.set_progress(0.1))
            time.sleep(0.3)

            git_dir = os.path.join(folder, ".git")
            if os.path.exists(git_dir):
                self._log_msg("  Removing existing .git for clean start...", "warn")
                try:
                    def _rm_ro(func, path, _exc):
                        os.chmod(path, 0o777)
                        func(path)
                    shutil.rmtree(git_dir, onerror=_rm_ro)
                    self._log_msg("  Old .git removed.", "ok")
                except Exception as exc:
                    self._log_msg(f"  Could not remove .git: {exc}", "warn")

            self._set_step_indicator(self._step4, "done", "Ready")

            # -- 2 git init ----
            self._set_step_indicator(self._step5, "running", "Initializing...")
            self._log_msg("\n[Step 2/6] Initializing Git repository...", "step")
            ok, *_ = self._run(["git", "init"], folder)
            if not ok:
                self._log_msg("  FAILED!", "err")
                self._set_step_indicator(self._step5, "error", "Failed")
                return
            self._log_msg("  Repository initialized.", "ok")
            self.root.after(0, lambda: self._progress.set_progress(0.25))
            time.sleep(0.2)

            if user:
                self._run(["git", "config", "user.name", user], folder)
            if email:
                self._run(["git", "config", "user.email", email], folder)

            # -- 3 git add ----
            self._log_msg("\n[Step 3/6] Staging all files...", "step")
            ok, *_ = self._run(["git", "add", "."], folder)
            if not ok:
                self._log_msg("  FAILED!", "err")
                self._set_step_indicator(self._step5, "error", "Failed")
                return
            self._log_msg("  All files staged.", "ok")
            self.root.after(0, lambda: self._progress.set_progress(0.4))
            time.sleep(0.2)

            # -- 4 git commit ----
            self._set_step_indicator(self._step5, "running", "Committing...")
            self._log_msg(f"\n[Step 4/6] Committing files...", "step")
            self._log_msg(f'  Message: "{commit}"', "info")
            ok, *_ = self._run(["git", "commit", "-m", commit], folder)
            if not ok:
                self._log_msg("  FAILED! Check folder has files & Step 7 identity.", "err")
                self._set_step_indicator(self._step5, "error", "Failed")
                return
            self._log_msg("  Commit created.", "ok")
            self._set_step_indicator(self._step5, "done", "Committed")
            self.root.after(0, lambda: self._progress.set_progress(0.55))
            time.sleep(0.2)

            # Branch rename
            self._set_step_indicator(self._step6, "running", "Setting branch...")
            self._run(["git", "branch", "-M", branch], folder)
            self._set_step_indicator(self._step6, "done", branch)

            # -- 5 git remote ----
            self._log_msg(f"\n[Step 5/6] Linking to {plat}...", "step")
            self._log_msg(f"  URL: {url}", "info")
            self._run(["git", "remote", "remove", "origin"], folder)
            ok, *_ = self._run(["git", "remote", "add", "origin", url], folder)
            if not ok:
                self._log_msg("  FAILED!", "err")
                return
            self._log_msg("  Remote linked.", "ok")
            self.root.after(0, lambda: self._progress.set_progress(0.7))
            time.sleep(0.2)

            # -- 6 Force push ----
            self._force_push(folder, branch, url, plat)

        except Exception as exc:
            self._log_msg(f"\nUnexpected error: {exc}", "err")
        finally:
            self._reset_ui_after_push(plat)

    # -----------------------------------------------------------------------
    # Force push with error detection
    # -----------------------------------------------------------------------
    def _force_push(self, folder, branch, url, plat):
        try:
            self._log_msg(f"\n[Step 6/6] Force-pushing to {plat}...", "step")
            self._log_msg("  This OVERWRITES the remote content.", "warn")
            self._log_msg(f"  A credential dialog may appear.", "info")
            self.root.after(0, lambda: self._progress.set_progress(0.85))

            ok, out, err = self._run(["git", "push", "--force", "origin", branch], folder)

            if ok:
                self.root.after(0, lambda: self._progress.complete())
                self._log_msg("")
                self._log_msg("  ╔══════════════════════════════════════════════════╗", "ok")
                self._log_msg(f"  ║     UPLOAD COMPLETED SUCCESSFULLY!               ║", "ok")
                self._log_msg("  ╚══════════════════════════════════════════════════╝", "ok")
                self._log_msg(f"\n  Your folder is now live at:\n  {url}", "ok")
                self.root.after(0, lambda: messagebox.showinfo(
                    "Success!", f"Pushed to {plat} successfully!\n\n{url}"))
                return

            self.root.after(0, lambda: self._progress.stop())
            combined = (out + " " + err).lower()

            if "protected branch" in combined:
                self._log_msg(f"\n  BLOCKED: '{branch}' is a PROTECTED branch.", "err")
                self._log_msg("")
                self._log_msg("  HOW TO FIX:", "warn")
                if plat == "GitLab":
                    self._log_msg("  1. Open your GitLab repo in a browser", "warn")
                    self._log_msg(f"     {url}", "info")
                    self._log_msg("  2. Settings > Repository > Protected branches", "warn")
                    self._log_msg(f"  3. Unprotect '{branch}' or allow force push", "warn")
                else:
                    self._log_msg("  1. Open your GitHub repo in a browser", "warn")
                    self._log_msg(f"     {url}", "info")
                    self._log_msg("  2. Settings > Branches > Branch protection rules", "warn")
                    self._log_msg(f"  3. Delete rule for '{branch}' or allow force pushes", "warn")
                self._log_msg("  4. Click RETRY PUSH below", "warn")
                self._show_retry_button(folder, branch, url, plat)

            elif any(x in combined for x in
                     ["authentication", "403", "401", "invalid username", "logon failed"]):
                self._log_msg("\n  Authentication error.", "err")
                if plat == "GitHub":
                    self._log_msg("  GitHub needs a Personal Access Token:", "warn")
                    self._log_msg("  Settings > Developer settings > Tokens > 'repo' scope", "warn")
                else:
                    self._log_msg("  GitLab needs a token with 'write_repository' scope.", "warn")
                self._show_retry_button(folder, branch, url, plat)

            elif "could not resolve host" in combined or "unable to access" in combined:
                self._log_msg("\n  Network / URL error.", "err")
                self._log_msg("  Check internet and repository URL.", "warn")
                self._show_retry_button(folder, branch, url, plat)

            elif "repository not found" in combined or "does not exist" in combined:
                self._log_msg("\n  Repository not found.", "err")
                self._log_msg(f"  Verify the repo exists: {url}", "warn")
                self._show_retry_button(folder, branch, url, plat)

            else:
                self._log_msg("\n  PUSH FAILED!", "err")
                self._log_msg("  Check URL, credentials, permissions, branch protection.", "warn")
                self._show_retry_button(folder, branch, url, plat)

        except Exception as exc:
            self._log_msg(f"\nError: {exc}", "err")
        finally:
            self._reset_ui_after_push(plat)

    def _show_retry_button(self, folder, branch, url, plat):
        def _retry():
            retry_btn.destroy()
            self.is_running = True
            self._push_btn.configure(state="disabled", text="     UPLOADING...     ")
            self._start_btn_pulse()
            self._start_spinner()
            self._progress.start_pulse()
            threading.Thread(target=self._force_push,
                             args=(folder, branch, url, plat), daemon=True).start()

        self._log_msg("\n  Fix the issue, then click Retry:", "info")

        retry_btn = tk.Button(
            self._log.master,
            text="     RETRY PUSH     ",
            font=("Segoe UI", 12, "bold"),
            bg=WARNING, fg="white", activebackground="#d97706",
            relief="flat", pady=10, cursor="hand2", command=_retry)
        self._add_hover(retry_btn, WARNING, "#d97706")
        self.root.after(0, lambda: retry_btn.pack(fill="x", pady=(8, 4)))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    root = tk.Tk()
    GitFolderUploader(root)
    root.mainloop()


if __name__ == "__main__":
    main()
