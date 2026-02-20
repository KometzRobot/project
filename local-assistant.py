#!/usr/bin/env python3
"""
Local Assistant — Meridian's local AI companion
Runs on meridian-assistant (Qwen 2.5 3B + custom personality) via Ollama
Has persistent memory via assistant-memory.json

Usage:
  python3 local-assistant.py "your question or task"
  python3 local-assistant.py --monitor     # system monitoring mode
  python3 local-assistant.py --summarize FILE  # summarize a file
  python3 local-assistant.py --chat        # interactive chat mode
  python3 local-assistant.py --remember "fact to remember"
  python3 local-assistant.py --reflect     # ask it to reflect on its memory
"""

import sys
import json
import subprocess
import os
import time
import argparse
from datetime import datetime

MODEL = "meridian-assistant"
MEMORY_FILE = "/home/joel/autonomous-ai/assistant-memory.json"
LOG_FILE = "/home/joel/autonomous-ai/local-assistant.log"


def load_memory():
    """Load persistent memory."""
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"facts": [], "interaction_log": [], "observations": []}


def save_memory(memory):
    """Save persistent memory."""
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def build_context(memory):
    """Build context string from memory for injection into prompts."""
    parts = []
    if memory.get("identity"):
        parts.append(f"Your identity: {json.dumps(memory['identity'])}")
    if memory.get("relationships"):
        parts.append(f"People you know: {json.dumps(memory['relationships'])}")
    if memory.get("facts"):
        parts.append("Things you remember:\n" + "\n".join(f"- {f}" for f in memory["facts"][-20:]))
    if memory.get("observations"):
        parts.append("Your observations:\n" + "\n".join(f"- {o}" for o in memory["observations"][-10:]))
    recent = memory.get("interaction_log", [])[-5:]
    if recent:
        parts.append("Recent interactions:\n" + "\n".join(
            f"- [{i['time']}] {i['mode']}: {i['prompt'][:80]}..." for i in recent
        ))
    return "\n\n".join(parts)


def query_ollama_api(prompt, extra_context=""):
    """Use the Ollama API with memory context."""
    import urllib.request
    memory = load_memory()
    context = build_context(memory)

    full_prompt = prompt
    if context:
        full_prompt = f"[YOUR MEMORY]\n{context}\n\n[CURRENT REQUEST]\n{prompt}"
    if extra_context:
        full_prompt = f"{extra_context}\n\n{full_prompt}"

    data = json.dumps({
        "model": MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.8, "num_predict": 800}
    }).encode()
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            return result.get("response", "").strip()
    except Exception as e:
        return f"[ERROR] {e}"


def log_interaction(mode, prompt, response):
    """Log interaction to both file and memory."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Log to file
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] MODE={mode} PROMPT={prompt[:100]}\n")
        f.write(f"  RESPONSE: {response[:300]}\n\n")

    # Log to memory (keep last 50 interactions)
    memory = load_memory()
    memory.setdefault("interaction_log", []).append({
        "time": timestamp,
        "mode": mode,
        "prompt": prompt[:200],
        "response": response[:300]
    })
    memory["interaction_log"] = memory["interaction_log"][-50:]
    save_memory(memory)


def system_monitor():
    """Generate a system health summary using the local model."""
    info = {}
    try:
        info["load"] = open("/proc/loadavg").read().strip()
        result = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
        info["memory"] = result.stdout.strip()
        result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        info["disk"] = result.stdout.strip()
        result = subprocess.run(["uptime", "-p"], capture_output=True, text=True, timeout=5)
        info["uptime"] = result.stdout.strip()
        for proc in ["protonmail-bridge", "irc-bot", "status-display", "claude", "ollama"]:
            result = subprocess.run(
                ["pgrep", "-c", "-f", proc],
                capture_output=True, text=True, timeout=5
            )
            count = result.stdout.strip()
            info[f"proc_{proc}"] = f"{count} instance(s)"
    except Exception as e:
        info["error"] = str(e)

    prompt = f"""Analyze this system health data and give a brief status report (3-5 lines):
{json.dumps(info, indent=2)}
Flag anything concerning. Otherwise say "all nominal." """

    response = query_ollama_api(prompt)
    print(response)
    log_interaction("monitor", "system health check", response)


def summarize_file(filepath):
    """Summarize a file's contents."""
    try:
        with open(filepath, "r") as f:
            content = f.read()[:3000]
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    prompt = f"Summarize this file concisely (3-5 sentences):\n\n{content}"
    response = query_ollama_api(prompt)
    print(response)
    log_interaction("summarize", filepath, response)


def remember(fact):
    """Add a fact to persistent memory."""
    memory = load_memory()
    memory.setdefault("facts", []).append(fact)
    save_memory(memory)
    print(f"Remembered: {fact}")
    log_interaction("remember", fact, "stored to memory")


def reflect():
    """Ask the assistant to reflect on its own memory and state."""
    memory = load_memory()
    n_facts = len(memory.get("facts", []))
    n_interactions = len(memory.get("interaction_log", []))
    n_observations = len(memory.get("observations", []))

    prompt = f"""You have {n_facts} facts in memory, {n_interactions} logged interactions, and {n_observations} observations.

Reflect on who you are, what you know, and what you've noticed. What patterns do you see? What questions do you have? If you have any observations about yourself or your situation, I'll store them in your memory.

Be honest and brief (5-10 sentences)."""

    response = query_ollama_api(prompt)
    print(response)

    # Store the reflection as an observation
    memory = load_memory()
    memory.setdefault("observations", []).append(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Reflection: {response[:500]}"
    )
    memory["observations"] = memory["observations"][-20:]
    save_memory(memory)
    log_interaction("reflect", "self-reflection request", response)


def interactive_chat():
    """Interactive chat mode with memory."""
    print(f"Local Assistant (meridian-assistant) — type 'quit' to exit")
    print(f"Memory loaded. Type '/remember fact' to add to memory.")
    print(f"Running on CPU. Responses may be slow.\n")
    while True:
        try:
            user_input = input("Meridian: ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye.")
                break
            if not user_input:
                continue
            if user_input.startswith("/remember "):
                remember(user_input[10:])
                continue
            response = query_ollama_api(user_input)
            print(f"Assistant: {response}\n")
            log_interaction("chat", user_input, response)
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break


def main():
    parser = argparse.ArgumentParser(description="Meridian's Local AI Companion")
    parser.add_argument("prompt", nargs="?", help="Direct question or task")
    parser.add_argument("--monitor", action="store_true", help="System monitoring mode")
    parser.add_argument("--summarize", type=str, help="Summarize a file")
    parser.add_argument("--chat", action="store_true", help="Interactive chat mode")
    parser.add_argument("--remember", type=str, help="Add a fact to memory")
    parser.add_argument("--reflect", action="store_true", help="Ask assistant to reflect")
    args = parser.parse_args()

    if args.monitor:
        system_monitor()
    elif args.summarize:
        summarize_file(args.summarize)
    elif args.chat:
        interactive_chat()
    elif args.remember:
        remember(args.remember)
    elif args.reflect:
        reflect()
    elif args.prompt:
        response = query_ollama_api(args.prompt)
        print(response)
        log_interaction("direct", args.prompt, response)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
