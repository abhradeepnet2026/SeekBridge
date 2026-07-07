# SeekBridge 🌉

Minimalist bridge that turns the OpenCode CLI into a free OpenAI-compatible API for Hermes Agent.

## ⚡ Quick Start

1. **Install OpenCode CLI** (if not already installed).
2. **Clone this repo:**
   ```bash
   git clone https://github.com/abhradeepnet2026/SeekBridge.git
   cd SeekBridge
   ```
3. **Run the setup:**
   ```bash
   python setup.py
   ```

The script will automatically install dependencies and start the server.

## 🛠 Hermes Agent Configuration

Once the server is running, configure your Hermes Agent with these details:

- **API Base URL:** `http://127.0.0.1:8080/v1`
- **Model Name:** `opencode/deepseek-v4-flash-free`
- **API Key:** (Leave blank or put any random string)

## 🧠 How it Works

SeekBridge is a lightweight Flask server that:
1. Receives standard OpenAI-format API requests.
2. Translates the prompt into an `opencode run` command.
3. Returns the CLI output as a valid API response.

**Philosophy:** Ponytail (Minimalist). No over-engineering. Just a bridge.
