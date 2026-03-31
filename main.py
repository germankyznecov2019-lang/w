import tkinter as tk
import threading
import time
import random
import os
import sys

# ---------------------------------------------------------------------------
# Stop-codes pool (realistic Windows kernel stop codes)
# ---------------------------------------------------------------------------
STOP_CODES = [
    "SYSTEM_SERVICE_EXCEPTION",
    "IRQL_NOT_LESS_OR_EQUAL",
    "KERNEL_SECURITY_CHECK_FAILURE",
    "PAGE_FAULT_IN_NONPAGED_AREA",
    "CRITICAL_PROCESS_DIED",
    "MEMORY_MANAGEMENT",
    "KMODE_EXCEPTION_NOT_HANDLED",
    "UNEXPECTED_KERNEL_MODE_TRAP",
    "DPC_WATCHDOG_VIOLATION",
    "DRIVER_IRQL_NOT_LESS_OR_EQUAL",
    "NTFS_FILE_SYSTEM",
    "BAD_POOL_HEADER",
    "SYSTEM_THREAD_EXCEPTION_NOT_HANDLED",
    "VIDEO_TDR_FAILURE",
    "WHEA_UNCORRECTABLE_ERROR",
]

BSOD_BLUE = "#0078D7"
WHITE     = "#FFFFFF"
LIGHT     = "#C8E6FF"   # slightly dimmer white for body text

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resource_path(relative: str) -> str:
    """Return absolute path whether running from source or PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def font(family: str, size: int, *styles) -> tuple:
    return (family, size) + styles


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class BSODApp:
    # Freeze points: {percentage: freeze_seconds}
    FREEZE_POINTS = {0: 6, 23: 8, 47: 10, 78: 7, 99: 12}

    def __init__(self):
        self.root = tk.Tk()
        self._setup_window()
        self._build_ui()
        self._bind_blockers()
        self.stop_code = random.choice(STOP_CODES)
        self.pct_var.set("0% complete")
        self.stop_label.config(text=f"Stop code: {self.stop_code}")
        # Start progress in background thread
        t = threading.Thread(target=self._run_progress, daemon=True)
        t.start()
        self.root.mainloop()

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self):
        r = self.root
        r.title("")
        r.configure(bg=BSOD_BLUE)
        r.attributes("-fullscreen", True)
        r.attributes("-topmost", True)
        r.overrideredirect(True)          # remove title-bar / decorations
        r.protocol("WM_DELETE_WINDOW", lambda: None)   # disable close button

    def _bind_blockers(self):
        """Block every keyboard and mouse event."""
        for seq in ("<Key>", "<KeyRelease>",
                    "<Button>", "<ButtonRelease>", "<Motion>",
                    "<MouseWheel>", "<Alt-F4>"):
            self.root.bind_all(seq, lambda e: "break")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        r = self.root
        W = r.winfo_screenwidth()
        H = r.winfo_screenheight()

        # ── canvas so we can place everything precisely ──────────────
        self.canvas = tk.Canvas(r, bg=BSOD_BLUE, highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # Margins (mimic Windows 11 BSOD proportions)
        left  = int(W * 0.14)
        top   = int(H * 0.18)

        # ── Sad face ─────────────────────────────────────────────────
        sad_size = max(72, int(H * 0.12))
        self.canvas.create_text(
            left, top,
            text=":(",
            font=font("Segoe UI", sad_size, "bold"),
            fill=WHITE, anchor="nw", tags="sad"
        )

        # ── Main headline ────────────────────────────────────────────
        headline_y = top + int(H * 0.155)
        headline_size = max(22, int(H * 0.038))
        self.canvas.create_text(
            left, headline_y,
            text="Your PC ran into a problem and needs to restart.",
            font=font("Segoe UI", headline_size, "bold"),
            fill=WHITE, anchor="nw", width=int(W * 0.72)
        )

        # ── Sub-headline ─────────────────────────────────────────────
        sub_y = headline_y + int(H * 0.085)
        sub_size = max(14, int(H * 0.024))
        self.canvas.create_text(
            left, sub_y,
            text="We're just collecting some error info, and then we'll restart for you.",
            font=font("Segoe UI", sub_size),
            fill=WHITE, anchor="nw", width=int(W * 0.72)
        )

        # ── Percentage line ──────────────────────────────────────────
        pct_y = sub_y + int(H * 0.12)
        pct_size = max(14, int(H * 0.024))
        self.pct_var = tk.StringVar(value="0% complete")
        self.pct_id = self.canvas.create_text(
            left, pct_y,
            textvariable=self.pct_var,
            font=font("Segoe UI", pct_size),
            fill=WHITE, anchor="nw"
        )

        # ── For more info ────────────────────────────────────────────
        info_y = pct_y + int(H * 0.065)
        info_size = max(12, int(H * 0.018))
        self.canvas.create_text(
            left, info_y,
            text="For more information about this issue and possible fixes, visit",
            font=font("Segoe UI", info_size),
            fill=LIGHT, anchor="nw"
        )
        self.canvas.create_text(
            left, info_y + int(H * 0.03),
            text="https://www.windows.com/stopcode",
            font=font("Segoe UI", info_size),
            fill=WHITE, anchor="nw"
        )

        # ── Stop code ────────────────────────────────────────────────
        code_y = info_y + int(H * 0.085)
        code_size = max(12, int(H * 0.018))
        self.stop_label = tk.Label(
            r, text="", bg=BSOD_BLUE, fg=WHITE,
            font=("Segoe UI", code_size)
        )
        self.stop_label.place(x=left, y=code_y)

        # ── Repair sequence label (hidden initially) ─────────────────
        repair_size = max(18, int(H * 0.030))
        self.repair_var = tk.StringVar(value="")
        self.repair_label = tk.Label(
            r, textvariable=self.repair_var,
            bg=BSOD_BLUE, fg=WHITE,
            font=("Segoe UI", repair_size, "bold"),
            wraplength=int(W * 0.65), justify="left"
        )
        self.repair_label.place(x=left, y=int(H * 0.45))
        self.repair_label.place_forget()      # hidden until needed

        # ── Final repair-fail message (hidden initially) ──────────────
        fail_size = max(14, int(H * 0.022))
        self.fail_var = tk.StringVar(value="")
        self.fail_label = tk.Label(
            r, textvariable=self.fail_var,
            bg=BSOD_BLUE, fg=WHITE,
            font=("Segoe UI", fail_size),
            wraplength=int(W * 0.60), justify="left"
        )
        self.fail_label.place(x=left, y=int(H * 0.55))
        self.fail_label.place_forget()

        # ── QR code image (bottom-left) ───────────────────────────────
        qr_path = resource_path("qr.png")
        self.qr_photo = None
        qr_bottom = int(H * 0.88)
        qr_size_hint = int(H * 0.12)

        if os.path.exists(qr_path):
            try:
                self.qr_photo = tk.PhotoImage(file=qr_path)
                # Scale to reasonable size using subsample / zoom
                orig_w = self.qr_photo.width()
                orig_h = self.qr_photo.height()
                if orig_w > 0 and orig_h > 0:
                    scale = max(1, orig_w // qr_size_hint)
                    if scale > 1:
                        self.qr_photo = self.qr_photo.subsample(scale, scale)
                self.canvas.create_image(
                    left, qr_bottom,
                    image=self.qr_photo, anchor="sw"
                )
                qr_text_y = qr_bottom + int(H * 0.005)
            except Exception:
                qr_text_y = qr_bottom
        else:
            # Draw a placeholder rectangle when qr.png is absent
            ph = qr_size_hint
            self.canvas.create_rectangle(
                left, qr_bottom - ph,
                left + ph, qr_bottom,
                outline=WHITE, width=2
            )
            self.canvas.create_text(
                left + ph // 2, qr_bottom - ph // 2,
                text="QR", font=font("Segoe UI", 14), fill=WHITE
            )
            qr_text_y = qr_bottom + int(H * 0.005)

        small_size = max(9, int(H * 0.014))
        self.canvas.create_text(
            left, qr_text_y,
            text="For more information, visit microsoft.com/stopcode",
            font=font("Segoe UI", small_size),
            fill=LIGHT, anchor="nw"
        )

        # Store layout metrics for later use
        self._left = left
        self._W = W
        self._H = H

    # ------------------------------------------------------------------
    # Progress simulation (runs in background thread)
    # ------------------------------------------------------------------

    def _run_progress(self):
        """Simulate slow, uneven progress with freezes."""
        pct = 0
        total_target = random.uniform(120, 300)   # total ~2–5 min
        # Build a list of (target_pct, speed_factor) segments to add realism
        segments = self._build_segments()

        for seg_start, seg_end, sleep_per_step in segments:
            for p in range(seg_start, seg_end + 1):
                # Freeze if this is a freeze point
                freeze = self.FREEZE_POINTS.get(p)
                if freeze:
                    self._set_pct(p)
                    time.sleep(freeze)
                else:
                    self._set_pct(p)
                    # small random jitter on sleep
                    jitter = random.uniform(0.7, 1.4)
                    time.sleep(sleep_per_step * jitter)

        # --- 100% reached; short pause then repair sequence -----------
        self._set_pct(100)
        time.sleep(3)

        self._show_repair_sequence()

    def _build_segments(self) -> list:
        """
        Returns list of (start_pct, end_pct, sleep_per_step).
        Slower around freeze-points, faster in between.
        """
        breakpoints = sorted(self.FREEZE_POINTS.keys()) + [100]
        segments = []
        prev = 0
        for bp in breakpoints:
            if bp == 0:
                prev = 0
                continue
            # base time for this segment (seconds per percent)
            base = random.uniform(0.4, 2.5)
            segments.append((prev, bp, base))
            prev = bp
        return segments

    def _set_pct(self, value: int):
        self.root.after(0, lambda v=value: self.pct_var.set(f"{v}% complete"))

    # ------------------------------------------------------------------
    # Post-progress repair sequence
    # ------------------------------------------------------------------

    def _show_repair_sequence(self):
        """Show Automatic Repair messages after 100%."""
        # Hide percentage, stop-code label, canvas items keep showing
        self.root.after(0, self._hide_progress_ui)
        time.sleep(1)

        steps = [
            ("Automatic Repair", 4),
            ("Diagnosing your PC...", 5),
            ("Attempting repairs...", 7),
        ]
        for msg, duration in steps:
            self.root.after(0, lambda m=msg: self._set_repair_text(m))
            time.sleep(duration)

        # Final failure message
        self.root.after(0, self._show_fail_message)

    def _hide_progress_ui(self):
        self.pct_var.set("")
        self.stop_label.config(text="")

    def _set_repair_text(self, msg: str):
        self.repair_var.set(msg)
        self.repair_label.place(x=self._left, y=int(self._H * 0.42))

    def _show_fail_message(self):
        self.repair_var.set("Automatic Repair")
        self.repair_label.place(x=self._left, y=int(self._H * 0.30))

        self.fail_var.set(
            "Automatic Repair couldn't repair your PC.\n\n"
            "Press \"Advanced options\" to try other options to repair your PC\n"
            "or \"Shut down\" to turn off your PC."
        )
        self.fail_label.place(x=self._left, y=int(self._H * 0.42))

        # Show two fake buttons
        self.root.after(0, self._show_repair_buttons)

    def _show_repair_buttons(self):
        btn_y = int(self._H * 0.72)
        btn_font = ("Segoe UI", max(11, int(self._H * 0.018)))

        for i, label in enumerate(["Advanced options", "Shut down"]):
            b = tk.Button(
                self.root, text=label,
                bg="#1a1a2e", fg=WHITE,
                activebackground="#333366", activeforeground=WHITE,
                font=btn_font, relief="flat", bd=0,
                padx=24, pady=10,
                # These buttons do nothing (simulation only)
                command=lambda: None
            )
            b.place(x=self._left + i * int(self._W * 0.18), y=btn_y)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    BSODApp()
      
