import tkinter as tk
from tkinter import scrolledtext, filedialog
import configparser
import threading
import time
import os
import re
import requests
from platformdirs import user_config_dir
import sys

APP_NAME = "DivineEcho"
CONFIG_FILENAME = "config.ini"
CONFIG_DIR = user_config_dir(APP_NAME)
CONFIG_FILE = os.path.join(CONFIG_DIR, CONFIG_FILENAME)


class DivineEchoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Divine Echo – PoE2 Trade Telegram Notifier")
        self.geometry("720x650")
        self.resizable(False, False)

        self.monitor_thread = None
        self.stop_monitor = threading.Event()

        self.bot_token = ''
        self.chat_id = ''

        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.create_widgets()
        self.load_config()


    def create_widgets(self):
        tk.Label(self, text="Telegram Bot Token:").pack(anchor='w', padx=10)
        self.bot_token_entry = tk.Entry(self, width=80)
        self.bot_token_entry.pack(padx=10, pady=2)

        tk.Label(self, text="Telegram Chat ID:").pack(anchor='w', padx=10)
        self.chat_id_entry = tk.Entry(self, width=80)
        self.chat_id_entry.pack(padx=10, pady=2)

        tk.Label(self, text="PoE2 Log File Path:").pack(anchor='w', padx=10)
        log_frame = tk.Frame(self, width=700, height=30)
        log_frame.pack(padx=10, pady=2)
        log_frame.pack_propagate(False)

        self.log_path_entry = tk.Entry(log_frame)
        self.log_path_entry.pack(fill='both', expand=True)
        self.log_path_entry.bind("<Button-1>", self.choose_log_file)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        self.start_btn = tk.Button(btn_frame, text="Start", command=self.start_monitor)
        self.start_btn.pack(side='left', padx=5)

        self.stop_btn = tk.Button(btn_frame, text="Stop", command=self.stop_monitoring, state='disabled')
        self.stop_btn.pack(side='left', padx=5)

        self.save_btn = tk.Button(btn_frame, text="Save Config", command=self.save_config)
        self.save_btn.pack(side='left', padx=5)

        tk.Label(self, text="Output Log:").pack(anchor='w', padx=10)
        self.output_box = scrolledtext.ScrolledText(self, height=20, state='disabled')
        self.output_box.pack(fill='both', expand=True, padx=10, pady=5)

        self.config_path_label = tk.Label(self, text=f"Using config: {CONFIG_FILE}", font=("Arial", 8))
        self.config_path_label.pack(side='bottom', anchor='w', padx=10, pady=(0, 5))

    def choose_log_file(self, event=None):
        path = filedialog.askopenfilename(
            title="Select PoE2 Log File",
            filetypes=[("Log files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self.log_path_entry.delete(0, tk.END)
            self.log_path_entry.insert(0, path)

    def load_config(self):
        config = configparser.ConfigParser()
        if not os.path.exists(CONFIG_FILE):
            config['telegram'] = {'bot_token': '', 'chat_id': ''}
            config['log'] = {'file_path': ''}
            with open(CONFIG_FILE, 'w') as f:
                config.write(f)

        config.read(CONFIG_FILE)

        bot_token = config.get('telegram', 'bot_token', fallback='')
        chat_id = config.get('telegram', 'chat_id', fallback='')
        log_path = config.get('log', 'file_path', fallback='')

        self.bot_token_entry.insert(0, bot_token)
        self.chat_id_entry.insert(0, chat_id)
        self.log_path_entry.insert(0, log_path)

        self.bot_token = bot_token
        self.chat_id = chat_id

    def save_config(self):
        bot_token = self.bot_token_entry.get().strip()
        chat_id = self.chat_id_entry.get().strip()
        log_path = self.log_path_entry.get().strip()

        config = configparser.ConfigParser()
        config['telegram'] = {'bot_token': bot_token, 'chat_id': chat_id}
        config['log'] = {'file_path': log_path}

        with open(CONFIG_FILE, 'w') as f:
            config.write(f)

        self.bot_token = bot_token
        self.chat_id = chat_id

        self.append_output("Config saved successfully.\n")

    def start_monitor(self):
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.append_output("Divine Echo is already running.\n")
            return

        self.save_btn.config(state='disabled')
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')

        self.stop_monitor.clear()
        self.monitor_thread = threading.Thread(target=self.run_echo, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        self.stop_monitor.set()
        self.save_btn.config(state='normal')
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.append_output("\nMonitoring stopped.\n")

    def append_output(self, text):
        self.output_box.config(state='normal')
        self.output_box.insert(tk.END, text)
        self.output_box.see(tk.END)
        self.output_box.config(state='disabled')

    def run_echo(self):
        if not all([self.bot_token, self.chat_id, self.log_path_entry.get().strip()]):
            self.append_output("Missing configuration. Please fill out all fields.\n")
            return

        pattern = re.compile(r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2} \d+ \w+ \[INFO Client \d+\] @From (\w+): (.+)$")
        log_path = self.log_path_entry.get().strip()
        self.append_output("Divine Echo is now listening for trade whispers...\n")

        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, os.SEEK_END)
                while not self.stop_monitor.is_set():
                    line = f.readline()
                    if not line:
                        time.sleep(0.2)
                        continue
                    match = pattern.match(line.strip())
                    if match:
                        username, message = match.groups()
                        formatted = f"*Trade whisper from {username}:*\n{message}"
                        self.send_to_telegram(formatted)
                        self.append_output(f"{username}: {message}\n")
        except FileNotFoundError:
            self.append_output("Log file not found.\n")
        except Exception as e:
            self.append_output(f"Error: {e}\n")

    def send_to_telegram(self, message):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            telegram_data = response.json()
            if not telegram_data.get("ok"):
                raise ValueError(f"Telegram error: {telegram_data['description']}")
        except requests.exceptions.RequestException as e:
            self.append_output(f"[Telegram Request Error] {e}\n")
        except ValueError as ve:
            self.append_output(f"[Telegram Error] {ve}\n")
        except Exception as e:
            self.append_output(f"[Unexpected Error] {e}\n")


if __name__ == "__main__":
    app = DivineEchoApp()
    app.mainloop()
