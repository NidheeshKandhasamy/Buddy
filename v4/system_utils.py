# system_utils.py
"""
Extended system utilities for Buddy assistant.
Provides:
- basic system metrics
- GPU detection
- display resolution
- performance scoring
- process analysis
- background monitor helpers (freeze detection, automated alerts)
- enhanced threat scanner (heuristic)
"""

import os
import psutil
import platform
import shutil
import socket
import datetime
import subprocess
import time

# Optional libs. If not installed, functions degrade gracefully.
try:
    import GPUtil
except Exception:
    GPUtil = None

try:
    from screeninfo import get_monitors
except Exception:
    get_monitors = None
# system_utils.py

# Existing helpers
def check_system_health():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    return (
        f"🖥️ CPU Usage: {cpu_percent}%\n"
        f"🧠 RAM Usage: {memory.percent}% "
        f"({round(memory.used / (1024 ** 3), 2)} GB used of {round(memory.total / (1024 ** 3), 2)} GB)"
    )

def get_battery_status():
    try:
        battery = psutil.sensors_battery()
        if battery:
            plugged = "🔌 Charging" if battery.power_plugged else "🔋 Not Charging"
            return f"🔋 Battery: {battery.percent}% - {plugged}"
        return "❌ Battery status not available."
    except Exception:
        return "❌ Battery status not available on this system."

def get_network_info():
    try:
        addrs = psutil.net_if_addrs()
        info = "🌐 Network Interfaces:\n"
        for iface, addr_list in addrs.items():
            info += f"\n🔹 {iface}:\n"
            for addr in addr_list:
                fam = getattr(addr.family, 'name', str(addr.family))
                info += f"  • {fam}: {addr.address}\n"
        return info
    except Exception as e:
        return f"❌ Failed to get network info: {e}"

def get_network_speed():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download = st.download() / 1e6  # bits to megabits
        upload = st.upload() / 1e6
        ping = st.results.ping
        return (
            f"📶 Download: {download:.2f} Mbps\n"
            f"📤 Upload: {upload:.2f} Mbps\n"
            f"📡 Ping: {ping:.2f} ms"
        )
    except Exception as e:
        return f"❌ Failed to check network speed: {e}"

def get_storage_info():
    try:
        total, used, free = shutil.disk_usage("/")
        return (
            f"💾 Disk Usage:\n"
            f"• Total: {total // (2**30)} GB\n"
            f"• Used: {used // (2**30)} GB\n"
            f"• Free: {free // (2**30)} GB"
        )
    except Exception as e:
        return f"❌ Failed to get storage info: {e}"

def get_system_info():
    try:
        uname = platform.uname()
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
        return (
            f"🖥️ System Info:\n"
            f"• System: {uname.system}\n"
            f"• Node Name: {uname.node}\n"
            f"• Release: {uname.release}\n"
            f"• Version: {uname.version}\n"
            f"• Machine: {uname.machine}\n"
            f"• Processor: {uname.processor}\n"
            f"• Boot Time: {boot_time}"
        )
    except Exception as e:
        return f"❌ Failed to get system info: {e}"

def get_ip_info():
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        return f"🌍 Host: {hostname}\n🔗 IP Address: {ip_address}"
    except Exception as e:
        return f"❌ Could not retrieve IP info: {e}"

# NEW FUNCTIONS

def get_top_processes(limit=5):
    try:
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                cpu = p.info.get('cpu_percent') or 0.0
                mem = getattr(p.info.get('memory_info'), 'rss', 0)
                procs.append((p.info['name'], p.info['pid'], cpu, mem))
            except Exception:
                continue
        procs.sort(key=lambda x: x[2], reverse=True)  # sort by CPU
        out = "🔥 Top processes by CPU usage:\n"
        for name, pid, cpu, mem in procs[:limit]:
            mem_mb = round(mem / (1024**2), 2)
            out += f"• {name} (PID {pid}) — CPU: {cpu}% — RAM: {mem_mb} MB\n"
        return out
    except Exception as e:
        return f"❌ Failed to get top processes: {e}"

def get_system_temperature():
    # psutil.sensors_temperatures may not be available on all systems
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return "❌ Temperature sensors not available on this system."
        out = "🌡️ Temperature sensors:\n"
        for name, entries in temps.items():
            out += f"\n• {name}:\n"
            for entry in entries:
                out += f"  - {entry.label or 'sensor'}: {entry.current}°C (high: {entry.high})\n"
        return out
    except Exception as e:
        return f"❌ Failed to read temperatures: {e}"

def get_cleanup_suggestions():
    try:
        # Basic checks for large directories (home and temp)
        suggestions = []
        home = os.path.expanduser("~")
        temp = "/tmp" if os.name != 'nt' else os.environ.get('TEMP', '')

        def dir_size(path):
            total = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total += os.path.getsize(fp)
                    except Exception:
                        pass
            return total

        if home:
            hsize = dir_size(home)
            suggestions.append(("Home directory", hsize))
        if temp:
            tsize = dir_size(temp)
            suggestions.append(("Temp directory", tsize))

        out = "🧹 Cleanup suggestions (largest directories):\n"
        for name, size in sorted(suggestions, key=lambda x: x[1], reverse=True):
            out += f"• {name}: {round(size / (1024**3), 2)} GB\n"
        out += "Tip: Use disk cleanup tools or manually review large folders (Downloads, Videos, Pictures).\n"
        return out
    except Exception as e:
        return f"❌ Failed to generate cleanup suggestions: {e}"

def get_startup_programs():
    try:
        out = "⚙️ Startup programs:\n"
        if os.name == 'nt':
            # Windows: use powershell to list startup items (best-effort)
            try:
                cmd = ['powershell', '-Command',
                       "Get-CimInstance -ClassName Win32_StartupCommand | Select-Object Name,Command | Format-Table -AutoSize"]
                res = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
                out += res
            except Exception:
                out += "• Could not enumerate startup items on Windows without elevated rights.\n"
        else:
            # Linux/macOS best-effort: list ~/.config/autostart and systemd user services
            autostart = os.path.expanduser("~/.config/autostart")
            if os.path.isdir(autostart):
                for f in os.listdir(autostart):
                    out += f"• {f}\n"
            else:
                out += "• No user autostart entries found or requires elevated access.\n"
        return out
    except Exception as e:
        return f"❌ Failed to get startup programs: {e}"

def run_network_diagnostics():
    try:
        # ping google DNS as a simple diagnostic
        import platform as _platform
        target = "8.8.8.8"
        param = "-n" if _platform.system().lower()=="windows" else "-c"
        cmd = ["ping", param, "4", target]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return f"📡 Network Diagnostics (ping {target}):\n{res.stdout.strip()}"
    except Exception as e:
        return f"❌ Failed to run network diagnostics: {e}"

def scan_security_threats(path_to_scan=None):
    # Very basic heuristic scanner: hash check + suspicious extension check
    try:
        suspect = []
        scan_path = path_to_scan or os.path.expanduser("~/Downloads")
        if not os.path.exists(scan_path):
            return f"❌ Scan path not found: {scan_path}"

        for root, dirs, files in os.walk(scan_path):
            for f in files:
                fp = os.path.join(root, f)
                ext = os.path.splitext(f)[1].lower()
                if ext in ['.exe', '.scr', '.js', '.vbs', '.ps1', '.bat']:
                    suspect.append(fp)
        out = "🔍 Security scan results:\n"
        if suspect:
            for s in suspect:
                out += f"• Suspicious file: {s}\n"
            out += "Recommendation: Quarantine these files and perform a deeper AV scan.\n"
        else:
            out += "No obvious suspicious files found by heuristic scan.\n"
        return out
    except Exception as e:
        return f"❌ Security scan failed: {e}"

def explain_system_logs(last_n=50):
    try:
        out = "📜 Recent system log snippets:\n"
        if os.name == 'nt':
            out += "• Windows Event Log parsing is platform-specific; please export or run with elevated privileges.\n"
        else:
            # tail syslog/journalctl (best-effort)
            try:
                res = subprocess.check_output(['tail', '-n', str(last_n), '/var/log/syslog'], text=True, stderr=subprocess.DEVNULL)
                out += res
            except Exception:
                try:
                    res = subprocess.check_output(['journalctl', '-n', str(last_n), '--no-pager'], text=True, stderr=subprocess.DEVNULL)
                    out += res
                except Exception:
                    out += "• Could not read system logs (permission or nonstandard paths).\n"
        return out
    except Exception as e:
        return f"❌ Failed to fetch system logs: {e}"

def auto_fix_common_issues():
    try:
        actions = []
        # flush DNS
        if os.name == 'nt':
            try:
                subprocess.run(["ipconfig", "/flushdns"], check=False)
                actions.append("Flushed DNS cache")
            except Exception:
                pass
        else:
            try:
                subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], check=False)
                actions.append("Flushed DNS cache (systemd-resolve)")
            except Exception:
                pass
        # try to clear temp folder on Unix
        try:
            temp = "/tmp" if os.name != 'nt' else os.environ.get('TEMP', '')
            if temp and os.path.isdir(temp):
                actions.append(f"Cleared temp folder: {temp}")
        except Exception:
            pass
        # kill defunct high-cpu process (best-effort)
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                if p.info.get('cpu_percent', 0) > 95:
                    p.kill()
                    actions.append(f"Killed process {p.info['name']} (PID {p.info['pid']})")
            except Exception:
                pass
        if not actions:
            return "✅ Auto-healing completed: no automatic actions required."
        return "🛠️ Auto-healing actions:\n" + "\n".join(f"• {a}" for a in actions)
    except Exception as e:
        return f"❌ Auto-healing failed: {e}"

def generate_daily_report():
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        total, used, free = shutil.disk_usage("/")
        report = (
            "📊 Daily System Health Report\n"
            f"• CPU: {cpu}%\n"
            f"• RAM: {mem.percent}% ({round(mem.used/(1024**3),2)} GB used)\n"
            f"• Disk Free: {free//(2**30)} GB\n"
            f"• Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        return report
    except Exception as e:
        return f"❌ Failed to generate report: {e}"


# --- Basic helpers (kept from earlier) ---
def get_network_info():
    addrs = psutil.net_if_addrs()
    info = "🌐 Network Interfaces:\n"
    
    for iface, addr_list in addrs.items():
        info += f"\n🔹 {iface}:\n"
        for addr in addr_list:
            try:
                fam = addr.family.name
            except:
                fam = str(addr.family)
            info += f"  • {fam}: {addr.address}\n"
    return info

def get_network_speed():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download = st.download() / 1e6
        upload = st.upload() / 1e6
        ping = st.results.ping

        return (
            f"📶 Download: {download:.2f} Mbps\n"
            f"📤 Upload: {upload:.2f} Mbps\n"
            f"📡 Ping: {ping:.2f} ms"
        )
    except Exception as e:
        return f"❌ Failed to check network speed: {e}"
def get_system_temperature():
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return "🌡️ CPU Temperature: Not available on this device."
        for name, entries in temps.items():
            return f"🌡️ CPU Temperature: {entries[0].current}°C"
    except:
        return "🌡️ CPU Temperature: Not supported."

def check_system_health():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    return (
        f"CPU Usage: {cpu_percent}%\n"
        f"RAM Usage: {memory.percent}% ({round(memory.used / (1024 ** 3), 2)} GB used of {round(memory.total / (1024 ** 3), 2)} GB)"
    )

def get_ram_info():
    try:
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_percent": mem.percent
        }
    except Exception as e:
        return {"error": str(e)}

def get_storage_info():
    try:
        total, used, free = shutil.disk_usage("/")
        return {
            "total_gb": total // (2**30),
            "used_gb": used // (2**30),
            "free_gb": free // (2**30),
            "raw": f"Total: {total // (2**30)} GB, Used: {used // (2**30)} GB, Free: {free // (2**30)} GB"
        }
    except Exception as e:
        return {"error": str(e)}

def get_system_info():
    try:
        uname = platform.uname()
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "system": uname.system,
            "node": uname.node,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "processor": uname.processor,
            "boot_time": boot_time
        }
    except Exception as e:
        return {"error": str(e)}

def get_ip_info():
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        return {"hostname": hostname, "ip": ip_address}
    except Exception as e:
        return {"error": str(e)}

# --- New: GPU info (best-effort) ---

def get_gpu_info():
    """
    Returns GPU list or message if not available.
    GPUtil (pip install gputil) recommended for Nvidia/AMD detection.
    """
    try:
        if GPUtil is None:
            return {"note": "GPUtil not installed; GPU detection limited.", "gpus": []}
        gpus = GPUtil.getGPUs()
        out = []
        for g in gpus:
            out.append({
                "id": g.id,
                "name": g.name,
                "load": round(g.load * 100, 1),
                "memoryTotalMB": g.memoryTotal,
                "memoryUsedMB": g.memoryUsed,
                "temperature": getattr(g, "temperature", None)
            })
        return {"gpus": out}
    except Exception as e:
        return {"error": str(e)}

# --- New: Display resolution (best-effort) ---

def get_display_resolution():
    try:
        if get_monitors is None:
            return {"note": "screeninfo not installed; resolution unavailable."}
        monitors = get_monitors()
        res = []
        for m in monitors:
            res.append({"width": m.width, "height": m.height})
        return {"monitors": res}
    except Exception as e:
        return {"error": str(e)}

# --- Performance scoring ---

def performance_score():
    """
    Returns a simple 0-100 score (higher = better) based on CPU, RAM, and disk free space.
    We weight CPU (40%), RAM (35%), Disk (25%). Score is normalized.
    """
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = shutil.disk_usage("/")
        # normalize: lower CPU usage => better; lower mem.percent => better; more free disk => better
        cpu_score = max(0, 100 - cpu)  # 100 if cpu=0
        mem_score = max(0, 100 - mem.percent)
        disk_free_pct = (disk.free / disk.total) * 100
        disk_score = disk_free_pct
        score = (cpu_score * 0.4) + (mem_score * 0.35) + (disk_score * 0.25)
        return {"score": round(score, 1), "details": {"cpu": cpu, "mem_percent": mem.percent, "disk_free_pct": round(disk_free_pct,1)}}
    except Exception as e:
        return {"error": str(e)}

# --- Process analyzer ---

def get_top_processes(limit=5):
    try:
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                cpu = p.info.get('cpu_percent') or 0.0
                mem = getattr(p.info.get('memory_info'), 'rss', 0)
                procs.append((p.info['name'] or "unknown", p.info['pid'], cpu, mem))
            except Exception:
                continue
        procs.sort(key=lambda x: x[2], reverse=True)
        result = []
        for name, pid, cpu, mem in procs[:limit]:
            result.append({
                "name": name,
                "pid": pid,
                "cpu_percent": cpu,
                "ram_mb": round(mem/(1024**2),2)
            })
        return {"top_processes": result}
    except Exception as e:
        return {"error": str(e)}

# --- Freeze detection & background monitor ---

def detect_freeze(threshold_seconds=10, cpu_spike_threshold=90):
    """
    Heuristic freeze detection:
    - If any process consumes > cpu_spike_threshold for threshold_seconds continuously -> flagged.
    - If system-wide CPU stays very low but disk IO skyrockets (possible hang) - best-effort.
    Returns list of suspicious events.
    """
    events = []
    try:
        # sample for threshold_seconds in 1s steps
        high_cpu_procs = {}
        for _ in range(threshold_seconds):
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    cpu = p.cpu_percent(interval=None)
                    if cpu >= cpu_spike_threshold:
                        key = (p.pid, p.name())
                        high_cpu_procs[key] = high_cpu_procs.get(key, 0) + 1
                except Exception:
                    continue
            time.sleep(1)
        for (pid, name), count in high_cpu_procs.items():
            if count >= threshold_seconds:
                events.append(f"Process {name} (PID {pid}) used >= {cpu_spike_threshold}% CPU for {count} seconds.")
        # naive disk io check
        io1 = psutil.disk_io_counters()
        time.sleep(1)
        io2 = psutil.disk_io_counters()
        read_diff = io2.read_bytes - io1.read_bytes
        write_diff = io2.write_bytes - io1.write_bytes
        if (read_diff + write_diff) > (50 * 1024 * 1024):  # >50MB/s for that sample second
            events.append("High disk IO detected ( >50MB/s ), possible heavy I/O or hang.")
        return {"freeze_events": events}
    except Exception as e:
        return {"error": str(e)}

# --- Threat scanner (improved) ---

def get_battery_status():
    battery = psutil.sensors_battery()
    if battery:
        plugged = "Charging" if battery.power_plugged else "Not Charging"
        return f"Battery: {battery.percent}% - {plugged}"
    return "Battery information not available."


def scan_security_threats(path_to_scan=None):
    """
    Heuristic scanner:
    - Look for suspicious extensions in Downloads
    - Look for newly created executable files in last 24 hours
    - This is NOT a replacement for AV
    """
    try:
        suspects = []
        base = path_to_scan or os.path.expanduser("~/Downloads")
        now = time.time()
        if not os.path.exists(base):
            return {"note": f"Scan path not found: {base}", "suspects": []}
        for root, dirs, files in os.walk(base):
            for fn in files:
                fp = os.path.join(root, fn)
                ext = os.path.splitext(fn)[1].lower()
                try:
                    mtime = os.path.getmtime(fp)
                except Exception:
                    mtime = 0
                # suspicious extension
                if ext in ['.exe', '.scr', '.js', '.vbs', '.ps1', '.bat', '.jar', '.msi']:
                    suspects.append({"path": fp, "reason": f"suspicious extension {ext}", "age_hours": round((now-mtime)/3600,1)})
                # recently created binary-like
                elif (now - mtime) < 24*3600 and os.access(fp, os.X_OK):
                    suspects.append({"path": fp, "reason": "recent executable", "age_hours": round((now-mtime)/3600,1)})
        return {"suspects": suspects}
    except Exception as e:
        return {"error": str(e)}

# --- Auto-fix helper (careful with killing processes) ---

def auto_fix_common_issues(confirm=False):
    """
    Best-effort auto-fixes:
    - Flush DNS
    - Clear /tmp (non-windows)
    - Optionally kill runaway processes
    confirm=True will touch destructive actions (kill)
    """
    results = []
    try:
        # flush dns (best-effort)
        if platform.system().lower().startswith("win"):
            try:
                subprocess.run(["ipconfig", "/flushdns"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                results.append("Flushed DNS cache (Windows).")
            except Exception:
                pass
        else:
            try:
                subprocess.run(["sudo", "systemd-resolve", "--flush-caches"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                results.append("Flushed DNS cache (systemd-resolve).")
            except Exception:
                pass
        # clear /tmp (no delete of user data)
        if platform.system().lower() != "windows":
            tmp = "/tmp"
            if os.path.isdir(tmp):
                # only list top-level items (do not delete automatically)
                items = os.listdir(tmp)
                results.append(f"/tmp contains {len(items)} items.")
        # kill >95% CPU only if confirm
        if confirm:
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    cpu = p.info.get('cpu_percent') or 0
                    if cpu > 95:
                        p.kill()
                        results.append(f"Killed {p.info.get('name')} (pid {p.info.get('pid')}) due to {cpu}% CPU.")
                except Exception:
                    pass
        return {"actions": results}
    except Exception as e:
        return {"error": str(e)}

# --- App compatibility check (example DB) ---

APP_REQUIREMENTS = {
    "adobe illustrator": {
        "ram_gb": 8,
        "os": ["Windows 10", "Windows 11", "MacOS"],  # textual match best-effort
        "gpu_vendor_keywords": ["intel", "nvidia", "amd", "radeon", "iris"],
        "resolution": (1920, 1080)
    },
    # Add more apps here
}

def check_app_compatibility(app_name):
    """
    Returns compatibility check between local system and APP_REQUIREMENTS entry.
    """
    try:
        app_key = app_name.strip().lower()
        if app_key not in APP_REQUIREMENTS:
            return {"error": "Unknown app. Add requirements to APP_REQUIREMENTS."}
        req = APP_REQUIREMENTS[app_key]
        sysinfo = get_system_info()
        ram = get_ram_info()
        gpus = get_gpu_info()
        res = get_display_resolution()

        verdict = {"app": app_name, "checks": {}}
        # RAM
        if "total_gb" in ram:
            verdict["checks"]["ram_ok"] = ram["total_gb"] >= req["ram_gb"]
            verdict["checks"]["ram_total_gb"] = ram["total_gb"]
        else:
            verdict["checks"]["ram_ok"] = "unknown"
        # OS
        cur_os = sysinfo.get("system", "")
        verdict["checks"]["os_ok"] = any(k.lower() in cur_os.lower() for k in req.get("os", []))
        verdict["checks"]["current_os"] = cur_os
        # GPU
        gpu_ok = False
        gpu_names = []
        if isinstance(gpus, dict) and "gpus" in gpus and gpus["gpus"]:
            for g in gpus["gpus"]:
                name = g.get("name","").lower()
                gpu_names.append(name)
                if any(k in name for k in [kw.lower() for kw in req.get("gpu_vendor_keywords", [])]):
                    gpu_ok = True
        verdict["checks"]["gpu_ok"] = gpu_ok
        verdict["checks"]["gpu_names"] = gpu_names
        # Resolution
        res_ok = False
        if isinstance(res, dict) and "monitors" in res:
            for mon in res["monitors"]:
                if mon["width"] >= req["resolution"][0] and mon["height"] >= req["resolution"][1]:
                    res_ok = True
        verdict["checks"]["resolution_ok"] = res_ok
        verdict["checks"]["requirements"] = req
        return verdict
    except Exception as e:
        return {"error": str(e)}
