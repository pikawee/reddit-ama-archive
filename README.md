# Reddit AMA Archive

A static viewer and archiver for Reddit AMAs. Threads are saved as static JSON and served through GitHub Pages or opened directly from your file system. Visitors can search and filter answers without Reddit accounts or API limits.

## How it works

- **Static storage**: Answers and questions are downloaded once into `assets/data/` as JSON and JavaScript files.
- **Client-side search and filters**: All searching and category filtering run locally in the browser.
- **Multi-thread support**: Switch between multiple archived AMAs from the top menu.
- **Dual fetching modes**: Download thread content using either headless Chromium or the Reddit API.
- **No build dependencies to view**: Open `index.html` directly in a browser or serve it with any HTTP server.

## Viewing an archive locally

### Open directly
Double-click `index.html` in your file manager. The page loads data using the companion script in `assets/data/` without browser CORS errors.

### Local server
Run the preview server:
```bash
python scripts/serve.py
```
This serves the project at `http://127.0.0.1:8080` and opens your default browser.

Or use Python's built-in HTTP server:
```bash
python -m http.server 8080 --bind 127.0.0.1
```

## Archiving a new thread

When you archive a thread, the script extracts questions answered by the guest and uses an LLM to categorize the topics discussed.

### 1. Set your API key

**PowerShell:**
```powershell
$env:GEMINI_API_KEY = "your_key_here"
```

**Bash / macOS / Linux:**
```bash
export GEMINI_API_KEY="your_key_here"
```

### 2. Run the fetch script

```bash
uv run python scripts/fetch_ama.py --url "<reddit_thread_url>" --user "<guest_username>" --avatar-url "<avatar_image_url>"
```

You can also pass the key, provider, and avatar as flags:
```bash
uv run python scripts/fetch_ama.py --url "<reddit_thread_url>" --user "<guest_username>" --avatar-url "<avatar_image_url>" --ai-provider gemini --api-key "<key>"
```

Supported providers:
- **Google Gemini**: Set `GEMINI_API_KEY` or `GOOGLE_API_KEY` (default: `gemini-3.6-flash`)
- **Anthropic Claude**: Set `ANTHROPIC_API_KEY` (default: `claude-3-5-haiku-20241022`)
- **OpenRouter**: Set `OPENROUTER_API_KEY` (default: `google/gemini-2.0-flash-001`)
- **OpenAI**: Set `OPENAI_API_KEY` (default: `gpt-4o-mini`)
- **Groq**: Set `GROQ_API_KEY` (default: `llama-3.3-70b-versatile`)
- **DeepSeek**: Set `DEEPSEEK_API_KEY` (default: `deepseek-chat`)
- **Mistral**: Set `MISTRAL_API_KEY` (default: `mistral-small-latest`)
- **Local Ollama**: `--ai-provider ollama` (default: `http://localhost:11434`, model: `llama3.2`)
- **OpenAI-compatible endpoints**: `--ai-provider generic --ai-base-url <url> --api-key <key>`

Optional arguments:
- `--avatar-url <url>`: Sets a custom guest avatar image link displayed in the viewer header and dropdown menu.

The script writes:
1. `assets/data/<thread_id>.json` and `<thread_id>.js` with the parsed Q&A pairs and avatar metadata.
2. An updated thread list in `assets/data/threads.json` and `threads.js`.

## Building for deployment

Run the build script:
```bash
python scripts/build.py
```

This validates your data and packages files into `dist/`. Test the build locally with:
```bash
python -m http.server 8000 --directory dist
```

## Deploying to GitHub Pages

### Initial setup
1. Push this repository to GitHub.
2. In your repository, go to **Settings** > **Pages**.
3. Under **Build and deployment** > **Source**, choose **GitHub Actions**.

### Add API keys for workflow runs
In your repository, go to **Settings** > **Secrets and variables** > **Actions** > **New repository secret**. Add your preferred provider key (such as `GEMINI_API_KEY` or `ANTHROPIC_API_KEY`).

### Automatic deployment
Every push to `main` triggers `.github/workflows/deploy.yml` to build and publish the site.

### Archive a thread from GitHub Actions
You can archive threads directly from GitHub without running Python locally:
1. Open the **Actions** tab.
2. Select **Deploy to GitHub Pages**.
3. Click **Run workflow**.
4. Enter the thread URL, username, optional custom avatar image URL, and provider.
5. Click **Run workflow**. The action fetches the thread, categorizes the answers, rebuilds the site, and deploys it.

## Repository layout

```text
├── assets/
│   └── data/
│       ├── threads.json       # List of archived threads
│       ├── 1w78hmo.json       # Carl Pei Q&A data
│       └── 1w78hmo.js         # Fallback data for file:/// protocol
├── scripts/
│   ├── fetch_ama.py           # Thread fetcher and categorizer
│   ├── build.py               # Static site generator for dist/
│   └── serve.py               # Local development server
├── tests/                     # Test suite
├── .github/workflows/         # GitHub Pages deploy workflow
├── index.html                 # Frontend viewer
└── README.md
```

## Acknowledgements

- Inspired by the Carl Pei Reddit AMA viewer by [@kustom_ai](https://x.com/kustom_ai) ([tweet](https://x.com/kustom_ai/status/2096201047685341573) / [demo](https://carl-pei-reddit-ama.kustom-ai.chatgpt.site/)).
