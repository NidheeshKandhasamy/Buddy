# main.py - Tkinter GUI with auto-monitoring and alerts
import tkinter as tk
import threading
from ai_handler import dispatch_input
import time
from functools import partial

AUTO_MONITOR_INTERVAL = 15  # seconds between checks in auto-monitor mode

root = tk.Tk()
root.title("Buddy — AI System Assistant (Enhanced)")
root.geometry("900x700")
root.configure(bg="#1a1a1a")

chat_log = tk.Text(root, bg="#1a1a1a", fg="white", font=("Consolas", 12), wrap=tk.WORD)
chat_log.tag_configure("user", foreground="#00d4ff")
chat_log.tag_configure("bot", foreground="#c586c0")
chat_log.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

entry = tk.Entry(root, font=("Consolas", 12), bg="#222222", fg="white")
entry.pack(fill=tk.X, padx=10, pady=(0, 10))
entry.bind("<Return>", lambda e: send_message())

send_button = tk.Button(root, text="Send", command=lambda: send_message(), bg="#007acc", fg="white")
send_button.pack(pady=(0, 10))

# Auto-monitor toggle
auto_var = tk.BooleanVar(value=False)
def toggle_auto():
    if auto_var.get():
        start_auto_monitor()
    else:
        stop_auto_monitor()

auto_check = tk.Checkbutton(root, text="Auto-Monitor (auto alerts)", variable=auto_var, command=toggle_auto, bg="#1a1a1a", fg="white", selectcolor="#1a1a1a")
auto_check.pack()

# small alert area
alert_frame = tk.Frame(root, bg="#2b2b2b")
alert_frame.pack(fill=tk.X, padx=10, pady=5)
alert_label = tk.Label(alert_frame, text="No alerts", bg="#2b2b2b", fg="#ffcc00", font=("Consolas", 11))
alert_label.pack(padx=5, pady=5)

thinking_index = None
auto_monitor_thread = None
_stop_auto = threading.Event()

def append_chat(text, tag="bot"):
    chat_log.config(state=tk.NORMAL)
    chat_log.insert(tk.END, text + "\n", tag)
    chat_log.config(state=tk.DISABLED)
    chat_log.see(tk.END)

def send_message():
    user_input = entry.get().strip()
    if not user_input:
        return
    append_chat(f"You: {user_input}", "user")
    entry.delete(0, tk.END)
    append_chat("🧠 AI: Thinking...", "bot")
    threading.Thread(target=process_input, args=(user_input,)).start()

def process_input(user_input):
    response = dispatch_input(user_input)
    # update UI on main
    root.after(0, lambda: replace_thinking_with(response))

def replace_thinking_with(response):
    # remove last "Thinking..." line if present
    content = chat_log.get("1.0", tk.END)
    if "🧠 AI: Thinking..." in content:
        idx = content.rfind("🧠 AI: Thinking...")
        chat_log.config(state=tk.NORMAL)
        chat_log.delete(f"1.0+{idx}c", f"1.0+{idx + len('🧠 AI: Thinking...')}c")
        chat_log.config(state=tk.DISABLED)
    append_chat(f"🧠 AI: {response}", "bot")

def background_auto_monitor():
    """
    Periodically run lightweight checks and push alerts to alert_label.
    Checks: performance_score, detect_freeze, scan_security_threats (light)
    """
    while not _stop_auto.is_set():
        try:
            perf = dispatch_input("what is my performance score?")  # uses LLM to route, but may be heavier
            # Instead of calling dispatch_input which triggers LLM, call ai_handler functions directly for lightweight checks
            from system_utils import performance_score, detect_freeze, scan_security_threats
            p = performance_score()
            freeze = detect_freeze(threshold_seconds=3, cpu_spike_threshold=95)
            threats = scan_security_threats()
            alerts = []
            if isinstance(p, dict) and p.get("score",0) < 50:
                alerts.append(f"Performance low (score {p.get('score')})")
            if isinstance(freeze, dict) and freeze.get("freeze_events"):
                alerts.append("Freeze events: " + "; ".join(freeze.get("freeze_events")))
            if isinstance(threats, dict) and threats.get("suspects"):
                alerts.append(f"Threats found: {len(threats.get('suspects'))}")
            if alerts:
                text = " | ".join(alerts)
                root.after(0, lambda: alert_label.config(text=text))
                # also append to chat_log
                root.after(0, lambda: append_chat(f"🛑 AUTO-ALERT: {text}", "bot"))
            else:
                root.after(0, lambda: alert_label.config(text="No alerts"))
        except Exception as e:
            root.after(0, lambda: alert_label.config(text=f"Monitor error: {e}"))
        # sleep
        _stop_auto.wait(AUTO_MONITOR_INTERVAL)

def start_auto_monitor():
    global auto_monitor_thread, _stop_auto
    _stop_auto.clear()
    auto_monitor_thread = threading.Thread(target=background_auto_monitor, daemon=True)
    auto_monitor_thread.start()
    append_chat("Auto-monitor started.", "bot")

def stop_auto_monitor():
    _stop_auto.set()
    append_chat("Auto-monitor stopped.", "bot")
    alert_label.config(text="No alerts")

# convenience demo buttons
demo_frame = tk.Frame(root, bg="#1a1a1a")
demo_frame.pack(fill=tk.X, padx=10, pady=5)
btn1 = tk.Button(demo_frame, text="Check Performance", command=lambda: threading.Thread(target=lambda: append_chat(dispatch_input("why is my pc slow?"), "bot")).start())
btn1.pack(side=tk.LEFT, padx=5)
btn2 = tk.Button(demo_frame, text="Can I Run Illustrator?", command=lambda: threading.Thread(target=lambda: append_chat(dispatch_input("Can my pc run Adobe Illustrator?"), "bot")).start())
btn2.pack(side=tk.LEFT, padx=5)
btn3 = tk.Button(demo_frame, text="Run Quick Threat Scan", command=lambda: threading.Thread(target=lambda: append_chat(dispatch_input("scan my downloads for threats"), "bot")).start())
btn3.pack(side=tk.LEFT, padx=5)

append_chat("🧠 Buddy Ready — ask about system health, app compatibility, or say 'scan my downloads for threats'.", "bot")

root.mainloop()
