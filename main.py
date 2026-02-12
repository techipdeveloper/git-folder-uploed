"""
Git Folder Uploader - Techip Developers
========================================
A user-friendly GUI application to upload entire folders to
GitHub or GitLab, overwriting existing repository contents
with a force push.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import sys
import shutil
import time

# ---------------------------------------------------------------------------
# PyInstaller resource helper
# ---------------------------------------------------------------------------
def resource_path(relative_path):
    """Get absolute path to resource - works for dev and PyInstaller bundle."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


# ---------------------------------------------------------------------------
# Theme colours (matching Techip brand)
# ---------------------------------------------------------------------------
BG_DARK       = "#1a1a2e"
BG_CARD       = "#16213e"
BG_INPUT      = "#0f3460"
ACCENT_BLUE   = "#3b82f6"
ACCENT_CYAN   = "#06b6d4"
ACCENT_PURPLE = "#a855f7"
ACCENT_ORANGE = "#f97316"
SUCCESS       = "#22c55e"
ERROR         = "#ef4444"
WARNING       = "#f59e0b"
TEXT_PRIMARY   = "#e2e8f0"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED     = "#64748b"
BTN_HOVER      = "#2563eb"

# Platform colours
GITHUB_CLR  = "#238636"
GITLAB_CLR  = "#fc6d26"

# Suppress console window on Windows
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
class GitFolderUploader:
    """Main application window."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Git Folder Uploader  |  Techip")
        self.root.geometry("780x980")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(True, True)
        self.root.minsize(720, 900)

        # --- variables ---
        self.platform     = tk.StringVar(value="github")
        self.repo_url     = tk.StringVar()
        self.folder_path  = tk.StringVar()
        self.commit_msg   = tk.StringVar(value="Initial commit of local folder contents")
        self.branch_name  = tk.StringVar(value="main")
        self.git_user     = tk.StringVar()
        self.git_email    = tk.StringVar()
        self.git_installed = False
        self.is_running    = False

        # --- try to load logo for window icon ---
        self._load_icon()

        # --- build UI ---
        self._build_ui()

        # --- auto-check git on startup ---
        self.root.after(600, self._check_git_installation)

    # -----------------------------------------------------------------------
    # helpers
    # -----------------------------------------------------------------------
    @property
    def _plat(self) -> str:
        """Return 'GitHub' or 'GitLab'."""
        return "GitHub" if self.platform.get() == "github" else "GitLab"

    # -----------------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------------
    def _load_icon(self):
        """Set window icon from logo.png (requires Pillow)."""
        try:
            from PIL import Image, ImageTk
            path = resource_path("logo.png")
            if os.path.exists(path):
                img = Image.open(path).resize((32, 32), Image.LANCZOS)
                self._icon_ref = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, self._icon_ref)
        except Exception:
            pass

    def _build_ui(self):
        """Assemble every widget."""
        # Scrollable canvas
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

        # ---- HEADER ----
        hdr = tk.Frame(self._frame, bg=BG_DARK, pady=12)
        hdr.pack(fill="x", padx=24)

        try:
            from PIL import Image, ImageTk
            logo_path = resource_path("logo.png")
            if os.path.exists(logo_path):
                img = Image.open(logo_path).resize((72, 72), Image.LANCZOS)
                self._logo_ref = ImageTk.PhotoImage(img)
                tk.Label(hdr, image=self._logo_ref, bg=BG_DARK).pack(side="left", padx=(0, 16))
        except Exception:
            pass

        title_box = tk.Frame(hdr, bg=BG_DARK)
        title_box.pack(side="left", fill="x")
        tk.Label(title_box, text="Git Folder Uploader",
                 font=("Segoe UI", 22, "bold"), fg=TEXT_PRIMARY, bg=BG_DARK).pack(anchor="w")
        tk.Label(title_box, text="Upload entire folders to GitHub or GitLab with one click",
                 font=("Segoe UI", 11), fg=TEXT_SECONDARY, bg=BG_DARK).pack(anchor="w")

        # gradient-like separator
        tk.Frame(self._frame, bg=ACCENT_BLUE, height=2).pack(fill="x", padx=24, pady=(0, 8))

        # ---- STEP 1  Git check ----
        s1 = self._card("Step 1 : Git Installation Check",
                        "Verifying that Git is installed on your computer. "
                        "If it is missing, you can install it with one click.")
        self._git_lbl = tk.Label(s1, text="  Checking...",
                                 font=("Segoe UI", 10), fg=WARNING, bg=BG_CARD)
        self._git_lbl.pack(anchor="w", padx=18, pady=(0, 4))

        self._install_btn = self._make_btn(s1, "Install Git",
                                           ACCENT_PURPLE, self._install_git)
        self._install_btn.pack(anchor="w", padx=18, pady=(0, 8))
        self._install_btn.pack_forget()

        # ---- STEP 2  Platform selector ----
        s2 = self._card("Step 2 : Choose Platform",
                        "Select where you want to upload your folder.")

        radio_frame = tk.Frame(s2, bg=BG_CARD)
        radio_frame.pack(anchor="w", padx=18, pady=(0, 8))

        style = ttk.Style()
        style.configure("GitHub.TRadiobutton",
                        background=BG_CARD, foreground=GITHUB_CLR,
                        font=("Segoe UI", 12, "bold"))
        style.configure("GitLab.TRadiobutton",
                        background=BG_CARD, foreground=GITLAB_CLR,
                        font=("Segoe UI", 12, "bold"))
        style.map("GitHub.TRadiobutton", background=[("active", BG_CARD)])
        style.map("GitLab.TRadiobutton", background=[("active", BG_CARD)])

        self._rb_github = ttk.Radiobutton(
            radio_frame, text="  GitHub", variable=self.platform,
            value="github", style="GitHub.TRadiobutton",
            command=self._on_platform_change)
        self._rb_github.pack(side="left", padx=(0, 30))

        self._rb_gitlab = ttk.Radiobutton(
            radio_frame, text="  GitLab", variable=self.platform,
            value="gitlab", style="GitLab.TRadiobutton",
            command=self._on_platform_change)
        self._rb_gitlab.pack(side="left")

        # ---- STEP 3  Repo URL ----
        s3 = self._card("Step 3 : Repository URL",
                        "")
        self._url_desc = tk.Label(s3, text="", font=("Segoe UI", 9),
                                  fg=TEXT_SECONDARY, bg=BG_CARD,
                                  wraplength=680, justify="left")
        self._url_desc.pack(anchor="w", padx=18, pady=(0, 4))
        self._url_entry_widget = self._entry(s3, self.repo_url, placeholder="")

        # ---- STEP 4  Folder ----
        s4 = self._card("Step 4 : Select Folder to Upload",
                        "Choose the local folder whose contents you want to push. "
                        "All files and sub-folders inside it will be uploaded.")
        row = tk.Frame(s4, bg=BG_CARD)
        row.pack(fill="x", padx=18, pady=(0, 10))
        e = tk.Entry(row, textvariable=self.folder_path,
                     font=("Consolas", 11), bg=BG_INPUT, fg=TEXT_PRIMARY,
                     insertbackground=TEXT_PRIMARY, relief="flat")
        e.pack(side="left", fill="x", expand=True, ipady=8, ipadx=10)
        self._make_btn(row, "  Browse  ", ACCENT_CYAN,
                       self._select_folder).pack(side="right", padx=(10, 0))

        # ---- STEP 5  Commit message ----
        s5 = self._card("Step 5 : Commit Message",
                        "Describe what you are uploading. You can keep the default message.")
        self._entry(s5, self.commit_msg)

        # ---- STEP 6  Branch ----
        s6 = self._card("Step 6 : Branch Name",
                        "The remote branch to push to (usually 'main' or 'master').")
        self._entry(s6, self.branch_name)

        # ---- STEP 7  Git identity (optional) ----
        s7 = self._card("Step 7 (optional) : Git Identity",
                        "If Git complains about missing user name / email, fill these in. "
                        "They are saved only inside this repository.")
        self._entry(s7, self.git_user,  placeholder="Your Name")
        self._entry(s7, self.git_email, placeholder="you@example.com")

        # ---- PUSH BUTTON ----
        pbf = tk.Frame(self._frame, bg=BG_DARK, pady=10)
        pbf.pack(fill="x", padx=24)
        self._push_btn = tk.Button(
            pbf, text="    UPLOAD TO GITHUB    ",
            font=("Segoe UI", 15, "bold"), bg=GITHUB_CLR, fg="white",
            activebackground=BTN_HOVER, activeforeground="white",
            relief="flat", pady=14, cursor="hand2",
            command=self._start_push)
        self._push_btn.pack(fill="x")
        self._warn_lbl = tk.Label(pbf,
                 text="Warning: This will OVERWRITE the remote repository contents!",
                 font=("Segoe UI", 9, "italic"), fg=ERROR, bg=BG_DARK)
        self._warn_lbl.pack(pady=(6, 0))

        # ---- LOG ----
        lg = self._card("Output Log",
                        "Real-time progress and command output appear below.")
        self._log = tk.Text(lg, height=14, font=("Consolas", 10),
                            bg="#080814", fg=TEXT_PRIMARY,
                            insertbackground=TEXT_PRIMARY, relief="flat",
                            wrap="word", state="disabled")
        self._log.pack(fill="both", expand=True, padx=18, pady=(0, 10))
        for tag, colour in [("info", ACCENT_CYAN), ("ok", SUCCESS),
                            ("err", ERROR), ("warn", WARNING),
                            ("step", ACCENT_PURPLE), ("cmd", "#818cf8")]:
            self._log.tag_configure(tag, foreground=colour,
                                    font=("Consolas", 10, "bold") if tag == "step" else ("Consolas", 10))

        # ---- FOOTER ----
        ft = tk.Frame(self._frame, bg=BG_DARK, pady=14)
        ft.pack(fill="x", padx=24)
        tk.Frame(ft, bg=TEXT_MUTED, height=1).pack(fill="x", pady=(0, 10))

        footer_inner = tk.Frame(ft, bg=BG_DARK)
        footer_inner.pack()
        try:
            from PIL import Image, ImageTk
            logo_path = resource_path("logo.png")
            if os.path.exists(logo_path):
                small = Image.open(logo_path).resize((28, 28), Image.LANCZOS)
                self._footer_logo_ref = ImageTk.PhotoImage(small)
                tk.Label(footer_inner, image=self._footer_logo_ref, bg=BG_DARK).pack(side="left", padx=(0, 8))
        except Exception:
            pass

        tk.Label(footer_inner, text="Developed by Techip Developers",
                 font=("Segoe UI", 11, "bold"), fg=TEXT_SECONDARY, bg=BG_DARK).pack(side="left")
        tk.Label(ft, text="v2.0.0",
                 font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_DARK).pack()

        # Initialise dynamic labels
        self._on_platform_change()

    # -----------------------------------------------------------------------
    # Platform toggle
    # -----------------------------------------------------------------------
    def _on_platform_change(self):
        """Update labels, colours and placeholders when the user switches platform."""
        plat = self._plat  # "GitHub" or "GitLab"
        clr  = GITHUB_CLR if plat == "GitHub" else GITLAB_CLR

        if plat == "GitHub":
            self._url_desc.configure(
                text="Paste the HTTPS URL of your GitHub repository.\n"
                     "Example: https://github.com/username/my-repo.git")
        else:
            self._url_desc.configure(
                text="Paste the HTTPS URL of your GitLab repository.\n"
                     "Example: https://gitlab.com/username/my-repo.git")

        self._push_btn.configure(text=f"    UPLOAD TO {plat.upper()}    ", bg=clr)

    # -----------------------------------------------------------------------
    # Widget helpers
    # -----------------------------------------------------------------------
    def _card(self, title: str, desc: str) -> tk.Frame:
        outer = tk.Frame(self._frame, bg=BG_CARD, bd=0)
        outer.pack(fill="x", padx=24, pady=6)
        inner = tk.Frame(outer, bg=BG_CARD, padx=18, pady=10)
        inner.pack(fill="x")
        tk.Label(inner, text=title, font=("Segoe UI", 12, "bold"),
                 fg=ACCENT_CYAN, bg=BG_CARD).pack(anchor="w")
        if desc:
            tk.Label(inner, text=desc, font=("Segoe UI", 9),
                     fg=TEXT_SECONDARY, bg=BG_CARD,
                     wraplength=680, justify="left").pack(anchor="w", pady=(2, 6))
        return inner

    def _entry(self, parent, var, placeholder=""):
        e = tk.Entry(parent, textvariable=var,
                     font=("Consolas", 11), bg=BG_INPUT, fg=TEXT_PRIMARY,
                     insertbackground=TEXT_PRIMARY, relief="flat")
        e.pack(fill="x", padx=18, pady=(0, 8), ipady=8, ipadx=10)
        if placeholder and not var.get():
            e.insert(0, placeholder)
            e.configure(fg=TEXT_MUTED)

            def _focus_in(_):
                if e.get() == placeholder:
                    e.delete(0, "end")
                    e.configure(fg=TEXT_PRIMARY)

            def _focus_out(_):
                if not e.get():
                    e.insert(0, placeholder)
                    e.configure(fg=TEXT_MUTED)

            e.bind("<FocusIn>", _focus_in)
            e.bind("<FocusOut>", _focus_out)
        return e

    @staticmethod
    def _make_btn(parent, text, colour, command):
        return tk.Button(parent, text=text,
                         font=("Segoe UI", 10, "bold"),
                         bg=colour, fg="white", activebackground=colour,
                         relief="flat", padx=16, pady=6,
                         cursor="hand2", command=command)

    # -----------------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------------
    def _log_msg(self, text: str, tag: str = "info"):
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
    # Step 1 -- Git check / install
    # -----------------------------------------------------------------------
    def _check_git_installation(self):
        try:
            r = subprocess.run(["git", "--version"],
                               capture_output=True, text=True, timeout=15,
                               creationflags=CREATE_NO_WINDOW)
            if r.returncode == 0:
                ver = r.stdout.strip()
                self._git_lbl.configure(text=f"  {ver}  -  Ready!", fg=SUCCESS)
                self.git_installed = True
                self._install_btn.pack_forget()
                self._log_msg(f"Git detected: {ver}", "ok")
                return
        except Exception:
            pass
        self._git_lbl.configure(
            text="  Git is NOT installed. Click 'Install Git' or install manually.",
            fg=ERROR)
        self.git_installed = False
        self._install_btn.pack(anchor="w", padx=18, pady=(0, 8))
        self._log_msg("Git is not installed on this computer.", "err")
        self._log_msg("Click 'Install Git' or download from https://git-scm.com/download/win", "warn")

    def _install_git(self):
        self._install_btn.configure(state="disabled", text="Installing...")
        self._log_msg("\n--- Installing Git via winget ---", "step")
        self._log_msg("This may take a few minutes. Please wait...", "info")

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
                    self._log_msg("You may need to RESTART this application for Git to be found.", "warn")
                    self.root.after(0, lambda: self._git_lbl.configure(
                        text="  Git installed! Restart the app if needed.", fg=SUCCESS))
                    self.git_installed = True
                else:
                    self._log_msg("Installation may have failed. Try installing manually.", "err")
                    if err:
                        self._log_msg(err.strip(), "err")
            except FileNotFoundError:
                self._log_msg("winget not available. Please install Git manually:", "err")
                self._log_msg("  https://git-scm.com/download/win", "warn")
            except subprocess.TimeoutExpired:
                self._log_msg("Installation timed out. Please install Git manually.", "err")
            except Exception as exc:
                self._log_msg(f"Error: {exc}", "err")
            finally:
                self.root.after(0, lambda: self._install_btn.configure(
                    state="normal", text="Install Git"))

        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # Step 4 -- Folder selection
    # -----------------------------------------------------------------------
    def _select_folder(self):
        path = filedialog.askdirectory(title="Select Folder to Upload")
        if path:
            self.folder_path.set(path)
            self._log_msg(f"Selected folder: {path}", "info")

    # -----------------------------------------------------------------------
    # Command runner (called from worker thread)
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
    def _start_push(self):
        plat = self._plat
        if self.is_running:
            messagebox.showwarning("Busy", "A push is already in progress!")
            return
        if not self.git_installed:
            messagebox.showerror("Git Required",
                                 "Git must be installed first (see Step 1).")
            return
        url = self.repo_url.get().strip()
        if not url:
            messagebox.showerror("Missing URL",
                                 f"Please enter your {plat} repository URL (Step 3).")
            return
        folder = self.folder_path.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Missing Folder",
                                 "Please select a valid folder to upload (Step 4).")
            return
        commit = self.commit_msg.get().strip()
        if not commit:
            messagebox.showerror("Missing Message",
                                 "Please enter a commit message (Step 5).")
            return
        branch = self.branch_name.get().strip()
        if not branch:
            messagebox.showerror("Missing Branch",
                                 "Please enter a branch name (Step 6).")
            return

        if not messagebox.askyesno(
                "Confirm Force Push",
                f"Platform: {plat}\n\n"
                f"This will OVERWRITE all contents in:\n{url}\n\n"
                f"With files from:\n{folder}\n\n"
                f"Branch: {branch}\n\n"
                "Are you sure you want to continue?"):
            return

        self.is_running = True
        self._push_btn.configure(state="disabled",
                                 text="    UPLOADING ...    ", bg=TEXT_MUTED)
        threading.Thread(target=self._do_push, daemon=True).start()

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

        btn_clr = GITHUB_CLR if plat == "GitHub" else GITLAB_CLR

        try:
            self._log_msg("\n" + "=" * 55, "step")
            self._log_msg(f"    STARTING {plat.upper()} UPLOAD PROCESS", "step")
            self._log_msg("=" * 55, "step")

            # -- 1 Navigate ---------------------------------------------------
            self._log_msg("\n[Step 1/6] Navigating to selected folder...", "step")
            self._log_msg(f"  Folder: {folder}", "info")
            if not os.path.isdir(folder):
                self._log_msg("  Folder does not exist!", "err")
                return
            self._log_msg("  Folder is accessible.", "ok")
            time.sleep(0.3)

            # Remove old .git if present
            git_dir = os.path.join(folder, ".git")
            if os.path.exists(git_dir):
                self._log_msg("  Existing .git directory found - removing for a clean start...", "warn")
                try:
                    def _rm_readonly(func, path, _exc):
                        os.chmod(path, 0o777)
                        func(path)
                    shutil.rmtree(git_dir, onerror=_rm_readonly)
                    self._log_msg("  Old .git removed.", "ok")
                except Exception as exc:
                    self._log_msg(f"  Could not remove .git: {exc}", "warn")

            # -- 2 git init ----------------------------------------------------
            self._log_msg("\n[Step 2/6] Initializing a new Git repository...", "step")
            self._log_msg("  This creates a fresh local repo inside your folder.", "info")
            ok, *_ = self._run(["git", "init"], folder)
            if not ok:
                self._log_msg("  FAILED to initialize repository!", "err")
                return
            self._log_msg("  Repository initialized.", "ok")
            time.sleep(0.2)

            if user:
                self._run(["git", "config", "user.name", user], folder)
            if email:
                self._run(["git", "config", "user.email", email], folder)

            # -- 3 git add . ---------------------------------------------------
            self._log_msg("\n[Step 3/6] Staging all files and sub-folders...", "step")
            self._log_msg("  Every file in the folder is being added to the staging area.", "info")
            ok, *_ = self._run(["git", "add", "."], folder)
            if not ok:
                self._log_msg("  FAILED to stage files!", "err")
                return
            self._log_msg("  All files staged.", "ok")
            time.sleep(0.2)

            # -- 4 git commit --------------------------------------------------
            self._log_msg(f"\n[Step 4/6] Committing staged files...", "step")
            self._log_msg(f'  Message: "{commit}"', "info")
            ok, *_ = self._run(["git", "commit", "-m", commit], folder)
            if not ok:
                self._log_msg("  FAILED to commit! Are there any files in the folder?", "err")
                self._log_msg("  If Git complains about user identity, fill in Step 7 and retry.", "warn")
                return
            self._log_msg("  Commit created.", "ok")
            time.sleep(0.2)

            # Rename branch
            self._log_msg(f"\n  Renaming branch to '{branch}'...", "info")
            self._run(["git", "branch", "-M", branch], folder)

            # -- 5 git remote add origin ---------------------------------------
            self._log_msg(f"\n[Step 5/6] Linking local repo to {plat}...", "step")
            self._log_msg(f"  Remote URL: {url}", "info")
            self._run(["git", "remote", "remove", "origin"], folder)
            ok, *_ = self._run(["git", "remote", "add", "origin", url], folder)
            if not ok:
                self._log_msg("  FAILED to add remote!", "err")
                return
            self._log_msg("  Remote linked.", "ok")
            time.sleep(0.2)

            # -- 6 git push --force --------------------------------------------
            self._force_push(folder, branch, url, plat)

        except Exception as exc:
            self._log_msg(f"\nUnexpected error: {exc}", "err")
        finally:
            self.is_running = False
            self.root.after(0, lambda: self._push_btn.configure(
                state="normal",
                text=f"    UPLOAD TO {plat.upper()}    ",
                bg=btn_clr))

    # -----------------------------------------------------------------------
    # Force push with smart error detection
    # -----------------------------------------------------------------------
    def _force_push(self, folder, branch, url, plat):
        btn_clr = GITHUB_CLR if plat == "GitHub" else GITLAB_CLR
        try:
            self._log_msg(f"\n[Step 6/6] Force-pushing to {plat}...", "step")
            self._log_msg("  This OVERWRITES the remote repository content.", "warn")
            self._log_msg(f"  A credential dialog may appear - enter your {plat} credentials.", "info")
            ok, out, err = self._run(["git", "push", "--force", "origin", branch], folder)

            if ok:
                self._log_msg("\n" + "=" * 55, "ok")
                self._log_msg(f"    UPLOAD TO {plat.upper()} COMPLETED SUCCESSFULLY!", "ok")
                self._log_msg("=" * 55, "ok")
                self._log_msg(f"\nYour folder has been uploaded to:\n  {url}", "ok")
                self.root.after(0, lambda: messagebox.showinfo(
                    "Success!",
                    f"Your folder was successfully pushed to {plat}!\n\n{url}"))
                return

            # ---- Detect specific errors ------------------------------------
            combined = (out + " " + err).lower()

            if "protected branch" in combined:
                self._log_msg(f"\n  PUSH BLOCKED: The '{branch}' branch is PROTECTED.", "err")
                self._log_msg("", "info")
                self._log_msg("  HOW TO FIX:", "warn")
                if plat == "GitLab":
                    self._log_msg("  1. Open your GitLab repository in a browser", "warn")
                    self._log_msg(f"     {url}", "info")
                    self._log_msg("  2. Go to  Settings > Repository > Protected branches", "warn")
                    self._log_msg(f"  3. Find '{branch}' and either:", "warn")
                    self._log_msg("       a) Click 'Unprotect' (re-protect later)", "warn")
                    self._log_msg("       b) Toggle 'Allow force push' to ON", "warn")
                else:
                    self._log_msg("  1. Open your GitHub repository in a browser", "warn")
                    self._log_msg(f"     {url}", "info")
                    self._log_msg("  2. Go to  Settings > Branches > Branch protection rules", "warn")
                    self._log_msg(f"  3. Find the rule for '{branch}' and either:", "warn")
                    self._log_msg("       a) Delete the protection rule", "warn")
                    self._log_msg("       b) Check 'Allow force pushes'", "warn")
                self._log_msg("  4. Come back here and click 'RETRY PUSH' below", "warn")
                self._log_msg("", "info")
                self._show_retry_button(folder, branch, url, plat)

            elif "authentication" in combined or "403" in combined or "401" in combined \
                    or "invalid username" in combined or "logon failed" in combined:
                self._log_msg("\n  PUSH FAILED: Authentication error.", "err")
                self._log_msg(f"  Make sure your {plat} credentials are correct.", "warn")
                if plat == "GitHub":
                    self._log_msg("  GitHub no longer accepts passwords for HTTPS.", "warn")
                    self._log_msg("  You need a Personal Access Token (PAT):", "warn")
                    self._log_msg("    GitHub > Settings > Developer settings > Personal access tokens", "warn")
                    self._log_msg("    Create a token with 'repo' scope, use it as your password.", "warn")
                else:
                    self._log_msg("  For HTTPS repos you may need a Personal Access Token:", "warn")
                    self._log_msg("    GitLab > Preferences > Access Tokens", "warn")
                    self._log_msg("    Create token with 'write_repository' scope.", "warn")
                self._show_retry_button(folder, branch, url, plat)

            elif "could not resolve host" in combined or "unable to access" in combined:
                self._log_msg("\n  PUSH FAILED: Network / URL error.", "err")
                self._log_msg("  Check your internet connection and repository URL.", "warn")
                self._show_retry_button(folder, branch, url, plat)

            elif "repository not found" in combined or "does not exist" in combined:
                self._log_msg("\n  PUSH FAILED: Repository not found.", "err")
                self._log_msg(f"  Make sure the repository exists on {plat}:", "warn")
                self._log_msg(f"    {url}", "info")
                self._log_msg("  Also verify you have write access to it.", "warn")
                self._show_retry_button(folder, branch, url, plat)

            else:
                self._log_msg("\n  PUSH FAILED!", "err")
                self._log_msg("  Common causes:", "warn")
                self._log_msg("    - Incorrect repository URL", "warn")
                self._log_msg("    - Invalid credentials / access token", "warn")
                self._log_msg("    - No write permission on the repository", "warn")
                self._log_msg("    - Protected branch (check repo settings)", "warn")
                self._show_retry_button(folder, branch, url, plat)

        finally:
            self.is_running = False
            self.root.after(0, lambda: self._push_btn.configure(
                state="normal",
                text=f"    UPLOAD TO {plat.upper()}    ",
                bg=btn_clr))

    def _show_retry_button(self, folder, branch, url, plat):
        def _retry():
            retry_btn.destroy()
            self.is_running = True
            self._push_btn.configure(state="disabled",
                                     text="    UPLOADING ...    ", bg=TEXT_MUTED)
            threading.Thread(target=self._force_push,
                             args=(folder, branch, url, plat), daemon=True).start()

        self._log_msg("  When you've fixed the issue, click Retry below:", "info")

        retry_btn = tk.Button(
            self._log.master,
            text="    RETRY PUSH (Step 6 only)    ",
            font=("Segoe UI", 11, "bold"),
            bg=WARNING, fg="white", activebackground="#d97706",
            relief="flat", pady=8, cursor="hand2",
            command=_retry)
        self.root.after(0, lambda: retry_btn.pack(fill="x", padx=18, pady=(0, 10)))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    root = tk.Tk()
    GitFolderUploader(root)
    root.mainloop()


if __name__ == "__main__":
    main()
