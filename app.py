import tkinter as tk


BG = "#f4efe7"
CARD = "#fffaf4"
CARD_ALT = "#f0e7da"
TEXT = "#2d241f"
MUTED = "#6b5d54"
ACCENT = "#d97757"
ACCENT_DARK = "#b85f42"
ACCENT_SOFT = "#f3c8b8"
SUCCESS = "#3f7d64"


class BreakReminderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Take a Break")
        self.root.geometry("360x430")
        self.root.minsize(360, 430)
        self.root.configure(bg=BG)

        self.interval_minutes = tk.IntVar(value=20)
        self.break_seconds = tk.IntVar(value=20)
        self.is_running = False
        self.remaining_seconds = self.interval_minutes.get() * 60
        self.timer_job = None
        self.break_job = None
        self.break_window = None
        self.break_remaining = 0

        self.status_text = tk.StringVar(value="Ready when you are")
        self.timer_text = tk.StringVar(value=self._format_seconds(self.remaining_seconds))
        self.session_text = tk.StringVar(value="Next pause in 20 minutes")

        self._build_ui()
        self._sync_timer_with_settings()
        self._update_buttons()

    def _build_ui(self) -> None:
        shell = tk.Frame(self.root, bg=BG, padx=18, pady=18)
        shell.pack(fill="both", expand=True)

        hero = tk.Frame(shell, bg=BG)
        hero.pack(fill="x", pady=(0, 14))

        tk.Label(
            hero,
            text="Take a Break",
            bg=BG,
            fg=TEXT,
            font=("Georgia", 22, "bold"),
        ).pack(anchor="w")

        tk.Label(
            hero,
            text="A calm reminder to rest your eyes for 20 seconds every 20 minutes.",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 11),
            justify="left",
            wraplength=300,
        ).pack(anchor="w", pady=(6, 0))

        timer_card = tk.Frame(shell, bg=CARD, highlightthickness=1, highlightbackground=CARD_ALT)
        timer_card.pack(fill="x", pady=(0, 14))

        tk.Label(
            timer_card,
            text="Focus Session",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", padx=16, pady=(16, 8))

        self.timer_label = tk.Label(
            timer_card,
            textvariable=self.timer_text,
            bg=CARD,
            fg=TEXT,
            font=("Consolas", 34, "bold"),
        )
        self.timer_label.pack(anchor="w", padx=16)

        tk.Label(
            timer_card,
            textvariable=self.status_text,
            bg=CARD,
            fg=SUCCESS,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", padx=16, pady=(6, 3))

        tk.Label(
            timer_card,
            textvariable=self.session_text,
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=16, pady=(0, 14))

        progress_shell = tk.Frame(timer_card, bg=CARD)
        progress_shell.pack(fill="x", padx=16, pady=(0, 16))

        self.progress_track = tk.Frame(progress_shell, bg=CARD_ALT, height=10)
        self.progress_track.pack(fill="x")
        self.progress_track.pack_propagate(False)

        self.progress_fill = tk.Frame(self.progress_track, bg=ACCENT, width=0, height=10)
        self.progress_fill.place(x=0, y=0, relheight=1.0)

        controls = tk.Frame(shell, bg=BG)
        controls.pack(fill="x", pady=(0, 14))

        self.start_button = self._make_button(controls, "Start", ACCENT, self.start_timer)
        self.start_button.pack(side="left", expand=True, fill="x")

        self.pause_button = self._make_button(controls, "Pause", "#e7ddd1", self.pause_timer, fg=TEXT)
        self.pause_button.pack(side="left", expand=True, fill="x", padx=8)

        self.reset_button = self._make_button(controls, "Reset", "#e7ddd1", self.reset_timer, fg=TEXT)
        self.reset_button.pack(side="left", expand=True, fill="x")

        settings_card = tk.Frame(shell, bg=CARD, highlightthickness=1, highlightbackground=CARD_ALT)
        settings_card.pack(fill="both", expand=True)

        tk.Label(
            settings_card,
            text="Session Settings",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w", padx=16, pady=(16, 12))

        self.interval_entry = self._make_setting_row(
            settings_card,
            "Reminder interval",
            "minutes",
            self.interval_minutes,
        )
        self.break_entry = self._make_setting_row(
            settings_card,
            "Break duration",
            "seconds",
            self.break_seconds,
        )

        note = tk.Label(
            settings_card,
            text="Tip: change the numbers, then press Start to begin a fresh timer.",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 10),
            wraplength=280,
            justify="left",
        )
        note.pack(anchor="w", padx=16, pady=(6, 16))

        self.interval_entry.bind("<FocusOut>", lambda _event: self._sync_timer_with_settings())
        self.break_entry.bind("<FocusOut>", lambda _event: self._sync_timer_with_settings())
        self.interval_entry.bind("<Return>", lambda _event: self._sync_timer_with_settings())
        self.break_entry.bind("<Return>", lambda _event: self._sync_timer_with_settings())

    def _make_button(self, parent: tk.Widget, text: str, bg: str, command, fg: str = "white") -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=ACCENT_DARK if bg == ACCENT else CARD_ALT,
            activeforeground=fg,
            relief="flat",
            bd=0,
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=9,
            cursor="hand2",
        )

    def _make_setting_row(
        self,
        parent: tk.Widget,
        label_text: str,
        unit_text: str,
        variable: tk.IntVar,
    ) -> tk.Entry:
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=16, pady=(0, 10))

        tk.Label(
            row,
            text=label_text,
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w")

        field = tk.Frame(row, bg=CARD)
        field.pack(fill="x", pady=(8, 0))

        entry = tk.Entry(
            field,
            textvariable=variable,
            bg="#fffefe",
            fg=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=CARD_ALT,
            highlightcolor=ACCENT,
            insertbackground=TEXT,
            font=("Segoe UI", 12),
            justify="center",
            width=6,
        )
        entry.pack(side="left", ipadx=8, ipady=8)

        tk.Label(
            field,
            text=unit_text,
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(12, 0))

        return entry

    def _sync_timer_with_settings(self) -> None:
        self.interval_minutes.set(max(1, self._safe_int(self.interval_minutes.get(), 20)))
        self.break_seconds.set(max(5, self._safe_int(self.break_seconds.get(), 20)))

        if not self.is_running and self.break_window is None:
            self.remaining_seconds = self.interval_minutes.get() * 60
            self.timer_text.set(self._format_seconds(self.remaining_seconds))
            self.status_text.set("Ready when you are")
            self.session_text.set(
                f"Next pause in {self.interval_minutes.get()} minute"
                f"{'' if self.interval_minutes.get() == 1 else 's'}"
            )
            self._update_progress()

    def _safe_int(self, value, fallback: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def _format_seconds(self, total_seconds: int) -> str:
        minutes, seconds = divmod(max(0, total_seconds), 60)
        return f"{minutes:02d}:{seconds:02d}"

    def start_timer(self) -> None:
        self._sync_timer_with_settings()

        if self.is_running:
            return

        if self.timer_job is not None:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

        if self.remaining_seconds <= 0 or self.remaining_seconds > self.interval_minutes.get() * 60:
            self.remaining_seconds = self.interval_minutes.get() * 60

        self.is_running = True
        self.status_text.set("Focus mode is on")
        self.session_text.set(f"Break for {self.break_seconds.get()} seconds when the timer ends")
        self._update_buttons()
        self._update_progress()
        self._schedule_next_tick()

    def pause_timer(self) -> None:
        self.is_running = False
        self.status_text.set("Paused")
        self.session_text.set("Press Start to continue this session")
        if self.timer_job is not None:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None
        self._update_buttons()

    def reset_timer(self) -> None:
        if self.timer_job is not None:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None

        self.is_running = False
        self.remaining_seconds = self.interval_minutes.get() * 60
        self.timer_text.set(self._format_seconds(self.remaining_seconds))
        if self.break_window is None:
            self.status_text.set("Ready when you are")
            self.session_text.set(
                f"Next pause in {self.interval_minutes.get()} minute"
                f"{'' if self.interval_minutes.get() == 1 else 's'}"
            )
        self._update_progress()
        self._update_buttons()

    def _schedule_next_tick(self) -> None:
        self.timer_job = self.root.after(1000, self._tick_timer)

    def _tick_timer(self) -> None:
        if not self.is_running:
            return

        self.remaining_seconds -= 1
        self.timer_text.set(self._format_seconds(self.remaining_seconds))
        self._update_progress()

        if self.remaining_seconds <= 0:
            self.timer_job = None
            self._show_break_popup()
            return

        self._schedule_next_tick()

    def _update_progress(self) -> None:
        total = max(1, self.interval_minutes.get() * 60)
        completed = total - max(0, self.remaining_seconds)
        ratio = min(1.0, max(0.0, completed / total))
        width = max(0, int(self.progress_track.winfo_width() * ratio))
        self.progress_fill.place(x=0, y=0, width=width, relheight=1.0)

    def _update_buttons(self) -> None:
        if self.is_running:
            self.start_button.config(state="disabled", bg=ACCENT_SOFT, cursor="arrow")
            self.pause_button.config(state="normal", bg="#e7ddd1", cursor="hand2")
        else:
            self.start_button.config(state="normal", bg=ACCENT, cursor="hand2")
            self.pause_button.config(state="normal", bg="#e7ddd1", cursor="hand2")

    def _show_break_popup(self) -> None:
        self.pause_timer()
        self.break_remaining = self.break_seconds.get()

        self.root.bell()
        self.status_text.set("Break time")
        self.session_text.set("Look away from the screen and breathe")

        popup = tk.Toplevel(self.root)
        popup.title("Take a Break")
        popup.geometry("420x320")
        popup.resizable(False, False)
        popup.configure(bg="#2f241f")
        popup.attributes("-topmost", True)
        popup.grab_set()
        popup.protocol("WM_DELETE_WINDOW", lambda: None)
        self.break_window = popup

        card = tk.Frame(popup, bg="#2f241f", padx=28, pady=28)
        card.pack(fill="both", expand=True)

        tk.Label(
            card,
            text="Step away for a moment",
            bg="#2f241f",
            fg="#fff7f1",
            font=("Georgia", 22, "bold"),
        ).pack(anchor="center", pady=(0, 12))

        tk.Label(
            card,
            text="Relax your shoulders, blink slowly, and focus on something far away.",
            bg="#2f241f",
            fg="#d9c9c0",
            font=("Segoe UI", 11),
            wraplength=320,
            justify="center",
        ).pack(anchor="center", pady=(0, 18))

        self.break_label = tk.Label(
            card,
            text=f"{self.break_remaining} sec",
            bg="#2f241f",
            fg="#fff7f1",
            font=("Consolas", 34, "bold"),
        )
        self.break_label.pack(anchor="center", pady=(0, 22))

        actions = tk.Frame(card, bg="#2f241f")
        actions.pack(fill="x")

        self._make_button(actions, "Skip", "#58443a", self._finish_break).pack(
            side="left", expand=True, fill="x"
        )
        self._make_button(actions, "Start Again", ACCENT, self._restart_from_popup).pack(
            side="left", expand=True, fill="x", padx=(10, 0)
        )

        self._tick_break()

    def _tick_break(self) -> None:
        if self.break_window is None:
            return

        self.break_label.config(text=f"{self.break_remaining} sec")

        if self.break_remaining <= 0:
            self._finish_break()
            return

        self.break_remaining -= 1
        self.break_job = self.root.after(1000, self._tick_break)

    def _restart_from_popup(self) -> None:
        self._close_break_popup()
        self.remaining_seconds = self.interval_minutes.get() * 60
        self.timer_text.set(self._format_seconds(self.remaining_seconds))
        self._update_progress()
        self.start_timer()

    def _finish_break(self) -> None:
        self._close_break_popup()
        self.remaining_seconds = self.interval_minutes.get() * 60
        self.timer_text.set(self._format_seconds(self.remaining_seconds))
        self._update_progress()
        self.start_timer()

    def _close_break_popup(self) -> None:
        if self.break_job is not None:
            self.root.after_cancel(self.break_job)
            self.break_job = None

        if self.break_window is not None:
            self.break_window.grab_release()
            self.break_window.destroy()
            self.break_window = None

        self.status_text.set("Ready for the next focus session")
        self.session_text.set(
            f"Next pause in {self.interval_minutes.get()} minute"
            f"{'' if self.interval_minutes.get() == 1 else 's'}"
        )
        self._update_buttons()


def main() -> None:
    root = tk.Tk()
    app = BreakReminderApp(root)
    root.update_idletasks()
    app._update_progress()
    root.mainloop()


if __name__ == "__main__":
    main()
