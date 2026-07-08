# SeekBridge

Async, streaming bridge that turns the OpenCode CLI into a free OpenAI-compatible API for Hermes Agent. Real-time SSE streaming, session continuity, and zero paid API keys.

## Quick Start

1. **Install OpenCode CLI** (if not already installed): https://opencode.sh
2. **Clone this repo:**
   ```bash
   git clone https://github.com/abhradeepnet2026/SeekBridge.git
   cd SeekBridge
   ```
3. **Run the setup:**
   ```bash
   python setup.py
   ```

SeekBridge starts at `http://127.0.0.1:8080/v1` with SSE streaming enabled.

## Hermes Agent Configuration

Since SeekBridge is OpenAI-compatible, point Hermes at it as a custom provider:

```bash
hermes config set model.provider custom
hermes config set model.base_url http://127.0.0.1:8080/v1
hermes config set model.api_key seekbridge
hermes config set model.default opencode/deepseek-v4-flash-free
```

That's it — Hermes now routes through the free DeepSeek model via OpenCode CLI. Paid API keys (OpenRouter, Anthropic, etc.) stay untouched unless you explicitly `hermes model` to switch back.

## How it Works

1. Hermes sends a standard OpenAI-format `/v1/chat/completions` request.
2. SeekBridge spawns `opencode run -m <model> --format json`.
3. Output streams to Hermes in real-time as OpenAI-compatible SSE chunks.
4. Session IDs from `opencode` are captured and reused automatically for multi-turn conversations.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /v1/chat/completions` | OpenAI-compatible chat (streaming + non-streaming) |
| `GET /v1/models` | Lists available models |
| `GET /health` | Server health check |

**Philosophy:** Ponytail (Minimalist). Async + streaming, no over-engineering.
