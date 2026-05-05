# ai_handler.py
import os
import requests
from system_utils import (
    check_system_health,
    get_battery_status,
    get_network_info,
    get_network_speed,
    get_storage_info,
    get_system_info,
    get_ip_info,
    get_top_processes,
    get_system_temperature,
    get_cleanup_suggestions,
    get_startup_programs,
    run_network_diagnostics,
    scan_security_threats,
    explain_system_logs,
    auto_fix_common_issues,
    generate_daily_report,
    performance_score,
    detect_freeze,
    check_app_compatibility
)

# Groq config - use environment variable
GROQ_API_KEY = "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"
if not GROQ_API_KEY:
    raise RuntimeError("Please set environment variable GROQ_API_KEY with your Groq API key.")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

function_map = {
    "Cpu_memory_RAM": check_system_health,
    "get_battery_status": get_battery_status,
    "get_network_info": get_network_info,
    "get_network_speed": get_network_speed,
    "get_storage_info": get_storage_info,
    "System_Version_processor_time": get_system_info,
    "get_ip_info": get_ip_info,
    # new
    "get_top_processes": get_top_processes,
    "get_system_temperature": get_system_temperature,
    "get_cleanup_suggestions": get_cleanup_suggestions,
    "get_startup_programs": get_startup_programs,
    "run_network_diagnostics": run_network_diagnostics,
    "scan_security_threats": scan_security_threats,
    "explain_system_logs": explain_system_logs,
    "auto_fix_common_issues": auto_fix_common_issues,
    "generate_daily_report": generate_daily_report,
    "performance_score": performance_score,
    "detect_freeze": detect_freeze,
    "check_app_compatibility": check_app_compatibility
}

def call_groq_chat(messages, timeout=25):
    payload = {"model": "llama-3.1-8b-instant", "messages": messages, "temperature": 0.25}
    r = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def get_ai_response(user_input, system_result, extra_instructions=None):
    try:
        system_prompt = "You are Buddy, an expert PC assistant. Explain results concisely and in plain language. First show essential findings, then suggested actions."
        if extra_instructions:
            system_prompt += " " + extra_instructions
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User question: {user_input}\n\nSystem output:\n{system_result}"}
        ]
        return call_groq_chat(messages)
    except Exception as e:
        return f"❌ AI Error: {e}"

def dispatch_input(user_input):
    """
    Enhanced dispatcher:
    - Asks LLM which function(s) to run (may return comma-separated names)
    - Runs them, aggregates outputs and sends back to LLM for explanation
    - Special handling for check_app_compatibility expects 'check_app_compatibility:<app name>' or 'can my pc run <app>'
    """
    try:
        # quick heuristics to catch app compatibility questions without sending to LLM
        low = user_input.strip().lower()
        if low.startswith("can my pc run") or low.startswith("can i run") or "can my" in low and "run" in low:
            # extract app name
            tokens = low.replace("?", "").split()
            # naive extraction: last two/three words
            app_name = " ".join(tokens[tokens.index("run")+1:]) if "run" in tokens else " ".join(tokens[-3:])
            # fallback to send to AI if app name too short
            if app_name:
                # run check_app_compatibility
                comp = check_app_compatibility(app_name)
                # build readable system_result
                system_result = f"Compatibility check for '{app_name}':\n{comp}"
                return get_ai_response(user_input, system_result)
        # otherwise ask LLM which functions to run
        messages = [
            {"role":"system",
             "content": (
                 "You are a system intent classifier. Given user text, return ONE or MORE function names (comma-separated) "
                 "from this list if a system diagnostic should run; otherwise return 'chat'.\n"
                 f"Available functions: {', '.join(function_map.keys())}\n\n"
                 "Guidelines:\n"
                 "- If user asks about system slow/lag -> Cpu_memory_RAM, performance_score, get_top_processes, get_storage_info\n"
                 "- If user asks about battery -> get_battery_status\n"
                 "- If user asks about internet -> get_network_info, get_network_speed, run_network_diagnostics\n"
                 "- If user asks about files or security -> scan_security_threats\n"
                 "- If user asks for logs -> explain_system_logs\n"
                 "- If user asks to auto-fix -> auto_fix_common_issues\n"
                 "- If user asks for a daily report -> generate_daily_report\n"
                 "- If user asks for temperature -> get_system_temperature\n"
                 "- If user asks about startup -> get_startup_programs\n"
                 "- If user asks about performance score -> performance_score\n"
                 "- If user asks about freezes -> detect_freeze\n"
             )},
            {"role":"user", "content": user_input}
        ]
        func_name = call_groq_chat(messages)
        if func_name.strip().lower() == "chat":
            return get_ai_response(user_input, "")

        # parse function names and possibly arguments
        func_names = [f.strip() for f in func_name.split(",")]
        results = ""
        executed_any = False
        for fn in func_names:
            if ":" in fn:
                # allow "check_app_compatibility:adobe illustrator"
                base, arg = fn.split(":",1)
                base = base.strip()
                arg = arg.strip()
                if base in function_map:
                    executed_any = True
                    try:
                        res = function_map[base](arg)
                    except TypeError:
                        res = function_map[base]()
                    results += f"\n\n--- {base}({arg}) ---\n{res}\n"
            else:
                if fn in function_map:
                    executed_any = True
                    try:
                        res = function_map[fn]()
                    except TypeError:
                        # function expects args
                        res = f"Function {fn} requires arguments and was not called."
                    results += f"\n\n--- {fn} ---\n{res}\n"
        if not executed_any:
            return get_ai_response(user_input, "")
        # Now ask AI to explain aggregated results
        return get_ai_response(user_input, results)
    except requests.exceptions.RequestException as re:
        return f"❌ Network/AI request failed: {re}"
    except Exception as e:
        return f"❌ Error handling input: {e}"
