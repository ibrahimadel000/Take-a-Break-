import json
import os
import threading
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageDraw
import pystray
from winotify import Notification
from datetime import datetime, timedelta
import random
import winsound
import socket
import sys

SETTINGS_FILE = "settings.json"
IPC_PORT = 49152 # Random high port for IPC

WELLNESS_PROMPTS = [
    "Blink rapidly for a few seconds to moisten your eyes.",
    "Look at an object at least 20 feet away for 20 seconds.",
    "Roll your eyes slowly in a circle, then reverse.",
    "Stretch your arms above your head and take a deep breath.",
    "Gently tilt your head from side to side to stretch your neck.",
    "Stand up and do a quick lap around your room.",
    "Place your palms over your closed eyes for a moment of darkness.",
    "Squeeze your shoulder blades together, then relax.",
]

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class BreakReminderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Take a Break")
        self.geometry("450x650")
        self.minsize(400, 600)
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        
        # Settings & State
        self.settings = self.load_settings()
        self._init_variables()
        
        ctk.set_appearance_mode(self.appearance_mode.get())
        
        self.is_running = False
        self.remaining_seconds = self._get_int_var(self.interval_minutes_var, 20) * 60
        self.timer_job = None
        self.break_job = None
        self.break_window = None
        self.break_remaining = 0
        self.is_long_break = False
        
        self.status_text = ctk.StringVar(value="Ready when you are")
        self.timer_text = ctk.StringVar(value=self._format_seconds(self.remaining_seconds))
        self.session_text = ctk.StringVar(value=f"Next pause in {self._get_int_var(self.interval_minutes_var, 20)} minutes")
        
        self._build_ui()
        self._update_stats_display()
        self._update_buttons()

    def _init_variables(self):
        self.interval_minutes_var = ctk.StringVar(value=str(self.settings.get("interval_minutes", 20)))
        self.break_seconds_var = ctk.StringVar(value=str(self.settings.get("break_seconds", 20)))
        self.long_break_minutes_var = ctk.StringVar(value=str(self.settings.get("long_break_minutes", 5)))
        self.long_break_after_var = ctk.StringVar(value=str(self.settings.get("long_break_after", 4)))
        
        self.appearance_mode = ctk.StringVar(value=self.settings.get("appearance_mode", "System"))
        self.meeting_mode = ctk.BooleanVar(value=self.settings.get("meeting_mode", False))
        
        self.breaks_history = self.settings.get("breaks_history", {})
        self.short_breaks_count = self.settings.get("short_breaks_count", 0) # Counter for long break logic

    def _get_int_var(self, var, fallback):
        try:
            return int(var.get())
        except (ValueError, tk.TclError):
            return fallback

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    return json.load(f)
            except Exception: pass
        return {}

    def save_settings(self):
        self.settings.update({
            "interval_minutes": self._get_int_var(self.interval_minutes_var, 20),
            "break_seconds": self._get_int_var(self.break_seconds_var, 20),
            "long_break_minutes": self._get_int_var(self.long_break_minutes_var, 5),
            "long_break_after": self._get_int_var(self.long_break_after_var, 4),
            "appearance_mode": self.appearance_mode.get(),
            "meeting_mode": self.meeting_mode.get(),
            "breaks_history": self.breaks_history,
            "short_breaks_count": self.short_breaks_count
        })
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f)
        except Exception: pass

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.tabview = ctk.CTkTabview(self, segmented_button_selected_color="#d97757")
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        self.tab_timer = self.tabview.add("Timer")
        self.tab_stats = self.tabview.add("Stats")
        self.tab_advanced = self.tabview.add("Advanced")
        
        self._build_timer_tab()
        self._build_stats_tab()
        self._build_advanced_tab()

    def _build_timer_tab(self):
        shell = ctk.CTkFrame(self.tab_timer, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Hero
        hero = ctk.CTkFrame(shell, fg_color="transparent")
        hero.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(hero, text="Take a Break", font=ctk.CTkFont(family="Georgia", size=24, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(hero, text="Stay healthy while you work.", text_color="gray", font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(2, 0))
        
        # Timer Card
        timer_card = ctk.CTkFrame(shell, corner_radius=10)
        timer_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(timer_card, text="Focus Session", text_color="gray", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))
        self.timer_label = ctk.CTkLabel(timer_card, textvariable=self.timer_text, font=ctk.CTkFont(family="Consolas", size=54, weight="bold"))
        self.timer_label.pack(anchor="w", padx=20)
        
        ctk.CTkLabel(timer_card, textvariable=self.status_text, text_color="#3f7d64", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=20, pady=(5, 0))
        ctk.CTkLabel(timer_card, textvariable=self.session_text, text_color="gray", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=20, pady=(0, 15))
        
        self.progress_bar = ctk.CTkProgressBar(timer_card, height=10, progress_color="#d97757")
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 20))
        self.progress_bar.set(0)
        
        # Controls
        controls = ctk.CTkFrame(shell, fg_color="transparent")
        controls.pack(fill="x", pady=(0, 15))
        controls.columnconfigure((0, 1, 2), weight=1)
        
        self.start_button = ctk.CTkButton(controls, text="Start", command=self.start_timer, fg_color="#d97757", hover_color="#b85f42", font=ctk.CTkFont(weight="bold"), height=40)
        self.start_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        self.pause_button = ctk.CTkButton(controls, text="Pause", command=self.pause_timer, fg_color="gray", hover_color="darkgray", height=40)
        self.pause_button.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.reset_button = ctk.CTkButton(controls, text="Reset", command=self.reset_timer, fg_color="gray", hover_color="darkgray", height=40)
        self.reset_button.grid(row=0, column=2, padx=(5, 0), sticky="ew")

        # Quick Settings
        q_card = ctk.CTkFrame(shell, corner_radius=10)
        q_card.pack(fill="x", pady=(0, 10))
        
        row1 = ctk.CTkFrame(q_card, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(row1, text="Interval (min):").pack(side="left")
        ctk.CTkEntry(row1, textvariable=self.interval_minutes_var, width=50, justify="center").pack(side="right")
        
        row2 = ctk.CTkFrame(q_card, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkLabel(row2, text="Break (sec):").pack(side="left")
        ctk.CTkEntry(row2, textvariable=self.break_seconds_var, width=50, justify="center").pack(side="right")

        self.meeting_mode_switch = ctk.CTkSwitch(shell, text="Meeting Mode (Silent)", variable=self.meeting_mode, command=self.save_settings, progress_color="#d97757")
        self.meeting_mode_switch.pack(pady=10)

    def _build_stats_tab(self):
        self.stats_container = ctk.CTkFrame(self.tab_stats, fg_color="transparent")
        self.stats_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(self.stats_container, text="Weekly History", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 15))
        
        self.stats_scroll = ctk.CTkScrollableFrame(self.stats_container, height=300)
        self.stats_scroll.pack(fill="both", expand=True)

    def _build_advanced_tab(self):
        shell = ctk.CTkFrame(self.tab_advanced, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(shell, text="Long Break Cycle", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(0, 10))
        
        r1 = ctk.CTkFrame(shell, fg_color="transparent")
        r1.pack(fill="x", pady=5)
        ctk.CTkLabel(r1, text="Long break every:").pack(side="left")
        ctk.CTkEntry(r1, textvariable=self.long_break_after_var, width=50).pack(side="right")
        ctk.CTkLabel(r1, text="breaks").pack(side="right", padx=5)

        r2 = ctk.CTkFrame(shell, fg_color="transparent")
        r2.pack(fill="x", pady=5)
        ctk.CTkLabel(r2, text="Long break duration:").pack(side="left")
        ctk.CTkEntry(r2, textvariable=self.long_break_minutes_var, width=50).pack(side="right")
        ctk.CTkLabel(r2, text="min").pack(side="right", padx=5)

        ctk.CTkLabel(shell, text="Appearance", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(20, 10))
        ctk.CTkOptionMenu(shell, values=["System", "Light", "Dark"], variable=self.appearance_mode, command=self._change_theme).pack(fill="x")

    def _update_stats_display(self):
        for widget in self.stats_scroll.winfo_children():
            widget.destroy()
            
        today = datetime.now().date()
        for i in range(7):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            count = self.breaks_history.get(date_str, 0)
            
            row = ctk.CTkFrame(self.stats_scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            label = "Today" if i == 0 else "Yesterday" if i == 1 else date.strftime("%A")
            ctk.CTkLabel(row, text=label, width=100, anchor="w").pack(side="left")
            
            # Simple progress bar as a graph
            max_breaks = max(self.breaks_history.values()) if self.breaks_history else 1
            ratio = count / max(10, max_breaks)
            bar = ctk.CTkProgressBar(row, width=150, height=12, progress_color="#d97757" if i == 0 else "gray")
            bar.pack(side="left", padx=10)
            bar.set(ratio)
            
            ctk.CTkLabel(row, text=str(count)).pack(side="right")

    def _change_theme(self, choice):
        ctk.set_appearance_mode(choice)
        self.save_settings()

    def _format_seconds(self, total_seconds: int) -> str:
        minutes, seconds = divmod(max(0, total_seconds), 60)
        return f"{minutes:02d}:{seconds:02d}"

    def _sync_timer_with_settings(self):
        interval = self._get_int_var(self.interval_minutes_var, 20)
        if not self.is_running and self.break_window is None:
            self.remaining_seconds = interval * 60
            self.timer_text.set(self._format_seconds(self.remaining_seconds))
            self.status_text.set("Ready when you are")
            self.session_text.set(f"Next pause in {interval} minutes")
            self._update_progress()

    def start_timer(self):
        self.save_settings()
        if self.is_running: return
        if self.timer_job: self.after_cancel(self.timer_job)
        
        interval = self._get_int_var(self.interval_minutes_var, 20)
        if self.remaining_seconds <= 0 or self.remaining_seconds > interval * 60:
            self.remaining_seconds = interval * 60
        
        self.is_running = True
        self.status_text.set("Focus mode is on")
        self._update_session_info()
        self._update_buttons()
        self._schedule_next_tick()

    def _update_session_info(self):
        target = self._get_int_var(self.long_break_after_var, 4)
        remaining = target - self.short_breaks_count
        if remaining <= 1:
            self.session_text.set("Next break will be a LONG break!")
        else:
            self.session_text.set(f"{remaining} sessions until long break")

    def pause_timer(self):
        self.is_running = False
        self.status_text.set("Paused")
        if self.timer_job: self.after_cancel(self.timer_job)
        self._update_buttons()

    def reset_timer(self):
        if self.timer_job: self.after_cancel(self.timer_job)
        self.is_running = False
        self.remaining_seconds = self._get_int_var(self.interval_minutes_var, 20) * 60
        self.timer_text.set(self._format_seconds(self.remaining_seconds))
        self.status_text.set("Ready when you are")
        self._update_session_info()
        self._update_progress()
        self._update_buttons()

    def _schedule_next_tick(self):
        self.timer_job = self.after(1000, self._tick_timer)

    def _tick_timer(self):
        if not self.is_running: return
        self.remaining_seconds -= 1
        self.timer_text.set(self._format_seconds(self.remaining_seconds))
        self._update_progress()
        if self.remaining_seconds <= 0:
            self._trigger_break()
        else:
            self.timer_job = self.after(1000, self._tick_timer)

    def _update_progress(self):
        total = max(1, self._get_int_var(self.interval_minutes_var, 20) * 60)
        self.progress_bar.set(min(1.0, (total - self.remaining_seconds) / total))

    def _update_buttons(self):
        self.start_button.configure(state="disabled" if self.is_running else "normal")

    def _trigger_break(self):
        self.pause_timer()
        
        # Long break logic
        self.short_breaks_count += 1
        limit = self._get_int_var(self.long_break_after_var, 4)
        
        if self.short_breaks_count >= limit:
            self.is_long_break = True
            self.break_remaining = self._get_int_var(self.long_break_minutes_var, 5) * 60
            self.short_breaks_count = 0
        else:
            self.is_long_break = False
            self.break_remaining = self._get_int_var(self.break_seconds_var, 20)

        # Notify
        if not self.meeting_mode.get():
            self._play_pop_sound()
            self._show_interactive_notification()
            self._show_break_popup()
        else:
            # In meeting mode, we just reset the timer automatically or wait
            self.status_text.set("Break skipped (Meeting Mode)")
            self.reset_timer()
            self.start_timer()

    def _show_interactive_notification(self):
        try:
            title = "Time for a Break!" if not self.is_long_break else "Time for a Long Break!"
            msg = random.choice(WELLNESS_PROMPTS)
            
            toast = Notification(
                app_id="Take A Break",
                title=title,
                msg=msg,
                duration="long"
            )
            
            # Use current exe path for buttons
            exe_path = sys.executable
            
            toast.add_actions(label="Skip Break", launch=f'"{exe_path}" --skip')
            toast.add_actions(label="Pause Timer", launch=f'"{exe_path}" --pause')
            
            toast.show()
        except Exception as e:
            print("Notification failed:", e)

    def _play_pop_sound(self):
        try:
            # Use the soft 'bubble' messaging sound
            sound_path = r"C:\Windows\Media\Windows Notify Messaging.wav"
            if os.path.exists(sound_path):
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
        except Exception:
            self.bell()

    def _show_break_popup(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Take a Break")
        popup.geometry("500x400")
        popup.attributes("-topmost", True)
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() - 500) // 2
        y = (popup.winfo_screenheight() - 400) // 2
        popup.geometry(f"+{x}+{y}")
        
        popup.transient(self) # Keep it on top of main window
        popup.protocol("WM_DELETE_WINDOW", self._finish_break)
        self.break_window = popup

        card = ctk.CTkFrame(popup, fg_color="transparent")
        card.pack(fill="both", expand=True, padx=40, pady=40)

        title = "Step away for a moment" if not self.is_long_break else "Time for a Long Rest"
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(family="Georgia", size=26, weight="bold")).pack(pady=(0, 20))
        
        # Wellness Prompt
        prompt = random.choice(WELLNESS_PROMPTS)
        ctk.CTkLabel(card, text=prompt, wraplength=400, justify="center", font=ctk.CTkFont(size=15, slant="italic"), text_color="#d97757").pack(pady=(0, 25))

        self.break_label = ctk.CTkLabel(card, text=self._format_seconds(self.break_remaining), font=ctk.CTkFont(family="Consolas", size=64, weight="bold"))
        self.break_label.pack(pady=(0, 35))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x")
        actions.columnconfigure((0, 1), weight=1)
        ctk.CTkButton(actions, text="Skip", command=self._finish_break, fg_color="gray", height=45).grid(row=0, column=0, padx=(0, 5), sticky="ew")
        ctk.CTkButton(actions, text="Start Again", command=self._finish_break, fg_color="#d97757", height=45).grid(row=0, column=1, padx=(5, 0), sticky="ew")

        self._tick_break()

    def _tick_break(self):
        if not self.break_window: return
        self.break_label.configure(text=self._format_seconds(self.break_remaining))
        if self.break_remaining <= 0:
            self._finish_break()
        else:
            self.break_remaining -= 1
            self.break_job = self.after(1000, self._tick_break)

    def _finish_break(self):
        # Log stats
        today_str = datetime.now().strftime("%Y-%m-%d")
        self.breaks_history[today_str] = self.breaks_history.get(today_str, 0) + 1
        self.save_settings()
        self._update_stats_display()
        
        if self.break_job: self.after_cancel(self.break_job)
        self.break_job = None
        if self.break_window:
            self.break_window.grab_release()
            self.break_window.destroy()
            self.break_window = None
        
        self.reset_timer()
        self.start_timer()

    # --- System Tray ---
    def create_tray_icon_image(self):
        image = Image.new('RGB', (64, 64), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((16, 16, 48, 48), fill=(217, 119, 87))
        return image

    def run_tray(self):
        menu = pystray.Menu(pystray.MenuItem("Show Timer", self.show_from_tray, default=True), pystray.MenuItem("Quit", self.quit_from_tray))
        self.tray_icon = pystray.Icon("TakeABreak", self.create_tray_icon_image(), "Take A Break", menu)
        self.tray_icon.run()

    def show_from_tray(self, icon, item):
        icon.stop()
        self.after(0, self.deiconify)

    def quit_from_tray(self, icon, item):
        icon.stop()
        self.after(0, self.quit)

    def hide_to_tray(self):
        self.withdraw()
        threading.Thread(target=self.run_tray, daemon=True).start()

    # --- IPC Listener ---
    def start_ipc_listener(self):
        def listen():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('127.0.0.1', IPC_PORT))
                    s.listen()
                    while True:
                        conn, addr = s.accept()
                        with conn:
                            data = conn.recv(1024).decode()
                            if data == "skip":
                                self.after(0, self._finish_break)
                            elif data == "pause":
                                self.after(0, self.pause_timer)
                            elif data == "show":
                                self.after(0, self.deiconify)
                except Exception:
                    pass
        threading.Thread(target=listen, daemon=True).start()

def main():
    # Check for command line arguments
    if len(sys.argv) > 1:
        cmd = sys.argv[1].strip("--").lower()
        if cmd in ["skip", "pause", "show"]:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.connect(('127.0.0.1', IPC_PORT))
                    s.sendall(cmd.encode())
                sys.exit(0)
            except Exception:
                # If can't connect, maybe app isn't running or port blocked
                pass

    app = BreakReminderApp()
    app.start_ipc_listener()
    app.mainloop()

if __name__ == "__main__":
    main()


