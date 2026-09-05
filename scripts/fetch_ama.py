#!/usr/bin/env python3
"""
scripts/fetch_ama.py - Dual-Mode Reddit AMA Fetcher & Dynamic Archive Parser
Extracts questions answered by a target AMA user and saves them as structured JSON/JS.
Dynamic AI categorization is mandatory on the first run for any new AMA thread.
No hardcoded category rules are used.
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request


def extract_thread_id_from_url(url: str) -> str:
    """Extracts the Reddit thread ID from a URL or returns the input if already an ID."""
    url = url.strip()
    match = re.search(r'/comments/([a-z0-9]+)', url, re.IGNORECASE)
    if match:
        return match.group(1)
    if re.match(r'^[a-z0-9]+$', url, re.IGNORECASE):
        return url
    raise ValueError(f"Unable to extract Reddit thread ID from: {url}")

def parse_json_from_llm_response(text: str) -> dict:
    """Extracts and parses JSON from raw LLM output, handling code fences."""
    match = re.search(r'\{.*\}', text.strip(), re.DOTALL)
    return json.loads(match.group(0) if match else text.strip())

def resolve_ai_provider_and_key(
    requested_provider: str = "auto",
    provided_key: str | None = None
) -> tuple[str, str | None]:
    """Resolves the AI provider and API key from arguments or environment variables."""
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    groq_key = os.environ.get("GROQ_API_KEY")
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    mistral_key = os.environ.get("MISTRAL_API_KEY")

    if requested_provider != "auto":
        key_map = {
            "gemini": provided_key or gemini_key,
            "anthropic": provided_key or anthropic_key,
            "openrouter": provided_key or openrouter_key,
            "openai": provided_key or openai_key,
            "groq": provided_key or groq_key,
            "deepseek": provided_key or deepseek_key,
            "mistral": provided_key or mistral_key,
            "ollama": None,
            "generic": provided_key
        }
        return requested_provider, key_map.get(requested_provider, provided_key)

    # Auto-detection from explicit key prefix or environment variables
    if provided_key:
        if provided_key.startswith("sk-ant-"):
            return "anthropic", provided_key
        if provided_key.startswith("sk-or-"):
            return "openrouter", provided_key
        if provided_key.startswith("gsk_"):
            return "groq", provided_key
        if provided_key.startswith(("AIza", "AQ.")):
            # Deduplicate accidental double-pasted key
            half_len = len(provided_key) // 2
            if len(provided_key) % 2 == 0 and provided_key[:half_len] == provided_key[half_len:]:
                provided_key = provided_key[:half_len]
            return "gemini", provided_key
        return "openai", provided_key

    if gemini_key:
        return "gemini", gemini_key
    if anthropic_key:
        return "anthropic", anthropic_key
    if openrouter_key:
        return "openrouter", openrouter_key
    if openai_key:
        return "openai", openai_key
    if groq_key:
        return "groq", groq_key
    if deepseek_key:
        return "deepseek", deepseek_key
    if mistral_key:
        return "mistral", mistral_key

    return "ollama", None

def ai_categorize_items(
    items: list[dict],
    provider: str = "auto",
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None
) -> tuple[list[str], list[dict]]:
    """
    Uses an LLM (Gemini, Anthropic, OpenRouter, OpenAI, Groq, DeepSeek, Mistral, or Ollama)
    to analyze the entire AMA transcript and generate 4 to 7 context-specific categories.
    No hardcoded categories are used.
    """
    if not items:
        return ["All"], items

    chosen_provider, resolved_key = resolve_ai_provider_and_key(provider, api_key)
    print(f"Generating dynamic categories via LLM provider: {chosen_provider}")

    q_data = [{"id": it["id"], "q": it["question_text"], "a": it["answer_text"]} for it in items]

    prompt_text = (
        "You are an expert editor categorizing a Reddit AMA (Ask Me Anything) interview.\n"
        "Carefully read all the questions and answers provided below.\n\n"
        "Instructions:\n"
        "1. Dynamically identify 4 to 7 distinct, high-level topic categories that best capture the actual discussions and questions in this specific AMA.\n"
        "   Do not use predefined, generic, or hardcoded buckets. Create category names directly from what users asked and what the guest discussed.\n"
        "2. Categorize every single question by its numeric ID.\n"
        "3. Return ONLY a valid JSON object matching this schema:\n"
        "{\n"
        '  "categories": ["Category A", "Category B", ...],\n'
        '  "assignments": {\n'
        '    "1": "Category A",\n'
        '    "2": "Category B",\n'
        "    ...\n"
        "  }\n"
        "}\n\n"
        f"Questions and Answers:\n{json.dumps(q_data, ensure_ascii=False)}"
    )

    result_json = None

    try:
        if chosen_provider == "gemini":
            if not resolved_key:
                raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is not set.")
            model_name = model or "gemini-3.6-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={resolved_key}"
            req_data = json.dumps({
                "contents": [{"parts": [{"text": prompt_text}]}],
                "generationConfig": {"response_mime_type": "application/json"}
            }).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_payload = json.loads(resp.read().decode("utf-8"))
                text = resp_payload["candidates"][0]["content"]["parts"][0]["text"]
                result_json = parse_json_from_llm_response(text)

        elif chosen_provider == "anthropic":
            if not resolved_key:
                raise ValueError("ANTHROPIC_API_KEY is not set.")
            model_name = model or "claude-3-5-haiku-20241022"
            url = "https://api.anthropic.com/v1/messages"
            req_data = json.dumps({
                "model": model_name,
                "max_tokens": 4096,
                "messages": [
                    {"role": "user", "content": prompt_text}
                ]
            }).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers={
                "Content-Type": "application/json",
                "x-api-key": resolved_key,
                "anthropic-version": "2023-06-01"
            })
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_payload = json.loads(resp.read().decode("utf-8"))
                text = resp_payload["content"][0]["text"]
                result_json = parse_json_from_llm_response(text)

        elif chosen_provider == "openrouter":
            if not resolved_key:
                raise ValueError("OPENROUTER_API_KEY is not set.")
            model_name = model or "google/gemini-2.0-flash-001"
            url = "https://openrouter.ai/api/v1/chat/completions"
            req_data = json.dumps({
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that outputs only valid JSON."},
                    {"role": "user", "content": prompt_text}
                ],
                "response_format": {"type": "json_object"}
            }).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {resolved_key}",
                "HTTP-Referer": "https://github.com/ama-archive",
                "X-Title": "Reddit AMA Archive"
            })
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_payload = json.loads(resp.read().decode("utf-8"))
                text = resp_payload["choices"][0]["message"]["content"]
                result_json = parse_json_from_llm_response(text)

        elif chosen_provider in ("openai", "groq", "deepseek", "mistral", "generic"):
            endpoint_defaults = {
                "openai": ("https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
                "groq": ("https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile"),
                "deepseek": ("https://api.deepseek.com/chat/completions", "deepseek-chat"),
                "mistral": ("https://api.mistral.ai/v1/chat/completions", "mistral-small-latest"),
                "generic": (f"{base_url.rstrip('/')}/chat/completions" if base_url else "http://localhost:1234/v1/chat/completions", "default")
            }
            default_url, default_model = endpoint_defaults.get(chosen_provider, ("https://api.openai.com/v1/chat/completions", "gpt-4o-mini"))
            url = base_url or default_url
            model_name = model or default_model

            if not resolved_key and chosen_provider != "generic":
                raise ValueError(f"{chosen_provider.upper()}_API_KEY is not set.")

            req_data = json.dumps({
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that outputs only valid JSON."},
                    {"role": "user", "content": prompt_text}
                ],
                "response_format": {"type": "json_object"}
            }).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            if resolved_key:
                headers["Authorization"] = f"Bearer {resolved_key}"

            req = urllib.request.Request(url, data=req_data, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_payload = json.loads(resp.read().decode("utf-8"))
                text = resp_payload["choices"][0]["message"]["content"]
                result_json = parse_json_from_llm_response(text)

        elif chosen_provider == "ollama":
            host = base_url or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            url = f"{host.rstrip('/')}/api/generate"
            model_name = model or "llama3.2"
            req_data = json.dumps({
                "model": model_name,
                "prompt": prompt_text,
                "format": "json",
                "stream": False
            }).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                resp_payload = json.loads(resp.read().decode("utf-8"))
                result_json = parse_json_from_llm_response(resp_payload.get("response", "{}"))

        else:
            raise ValueError(f"Unknown AI provider: {chosen_provider}")

    except Exception as e:
        print(f"Error during AI categorization: {e}", file=sys.stderr)
        raise

    if not result_json or "categories" not in result_json or "assignments" not in result_json:
        raise ValueError("AI response did not return the expected categories and assignments schema.")

    assignments = result_json.get("assignments", {})
    categories = ["All"]
    for cat in result_json.get("categories", []):
        cat_str = str(cat).strip()
        if cat_str and cat_str != "All" and cat_str not in categories:
            categories.append(cat_str)

    for item in items:
        item_id_str = str(item["id"])
        assigned_cat = assignments.get(item_id_str) or (categories[1] if len(categories) > 1 else "Discussion")
        item["category"] = assigned_cat
        item["search_text"] = f"{item['question_text']} {item['answer_text']} {item['question_author']} {assigned_cat}".lower()
        if assigned_cat not in categories:
            categories.append(assigned_cat)

    print(f"Successfully generated {len(categories) - 1} dynamic categories via AI.")
    return categories, items

def pair_questions_and_answers(comments: list[dict], target_user: str) -> list[dict]:
    """
    Pairs each comment made by target_user with its parent comment (the question).
    Returns a sorted list of Q&A items without hardcoded categories.
    """
    target_clean = target_user.lower().replace("u/", "")
    comment_map: dict[str, dict] = {}
    for c in comments:
        cid = c.get("id", "").replace("t1_", "")
        if cid:
            comment_map[cid] = c

    items: list[dict] = []
    item_counter = 1

    for c in comments:
        author = c.get("author", "").lower().replace("u/", "")
        if author == target_clean:
            parent_id = c.get("parent_id", "").replace("t1_", "").replace("t3_", "")
            parent_comment = comment_map.get(parent_id, {})
            
            q_text = parent_comment.get("body", "").strip() or "Question not available or deleted"
            q_author = parent_comment.get("author", "anonymous")
            if q_author and not q_author.startswith("u/"):
                q_author = f"u/{q_author}"
                
            a_text = c.get("body", "").strip()
            a_author = c.get("author", target_user)
            if not a_author.startswith("u/"):
                a_author = f"u/{a_author}"
                
            permalink = c.get("permalink", "")
            if permalink and not permalink.startswith("http"):
                permalink = f"https://www.reddit.com{permalink}"

            cat = c.get("category", "")
            search_str = f"{q_text} {a_text} {q_author}".lower()

            items.append({
                "id": item_counter,
                "category": cat,
                "question_author": q_author,
                "question_text": q_text,
                "answer_author": a_author,
                "answer_text": a_text,
                "permalink": permalink,
                "search_text": search_str
            })
            item_counter += 1

    return items

def fetch_with_api(thread_id: str, client_id: str, client_secret: str, target_user: str) -> tuple[dict, list[dict]]:
    """Fetches thread comments using Reddit OAuth Client Credentials."""
    import base64

    auth_str = f"{client_id}:{client_secret}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    token_url = "https://www.reddit.com/api/v1/access_token"
    data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    headers = {
        "User-Agent": "AMAArchive/1.0.0",
        "Authorization": f"Basic {b64_auth}"
    }

    req = urllib.request.Request(token_url, data=data, headers=headers)
    with urllib.request.urlopen(req) as response:
        token_data = json.loads(response.read().decode())
        access_token = token_data.get("access_token")

    api_url = f"https://oauth.reddit.com/comments/{thread_id}.json?limit=500&depth=10"
    api_headers = {
        "User-Agent": "AMAArchive/1.0.0",
        "Authorization": f"Bearer {access_token}"
    }
    api_req = urllib.request.Request(api_url, headers=api_headers)
    with urllib.request.urlopen(api_req) as response:
        payload = json.loads(response.read().decode())

    post_data = payload[0]["data"]["children"][0]["data"]
    raw_comments = []

    def extract_replies(children):
        for child in children:
            if child.get("kind") == "t1":
                cdata = child["data"]
                raw_comments.append({
                    "id": cdata.get("id"),
                    "parent_id": cdata.get("parent_id"),
                    "author": cdata.get("author", "[deleted]"),
                    "body": cdata.get("body", ""),
                    "permalink": cdata.get("permalink", "")
                })
                replies = cdata.get("replies")
                if isinstance(replies, dict):
                    extract_replies(replies.get("data", {}).get("children", []))

    extract_replies(payload[1]["data"]["children"])

    items = pair_questions_and_answers(raw_comments, target_user)
    created_utc = post_data.get("created_utc")
    created_iso = ""
    date_str = ""
    if created_utc:
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(created_utc, timezone.utc)
        created_iso = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        date_str = dt.strftime("%b %d, %Y")

    meta = {
        "thread_id": thread_id,
        "title": post_data.get("title", f"AMA Thread {thread_id}"),
        "subreddit": f"r/{post_data.get('subreddit', 'Reddit')}",
        "original_url": f"https://www.reddit.com{post_data.get('permalink', '')}",
        "created_utc": int(created_utc) if created_utc else None,
        "created_iso": created_iso,
        "date": date_str
    }
    return meta, items

def fetch_with_headless(url: str, target_user: str) -> tuple[dict, list[dict]]:
    """Uses Playwright headless Chromium to load the thread and extract comments."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Error: Playwright is required for headless fetching.\n"
            "Run using: uv run --with playwright python scripts/fetch_ama.py ...\n"
            "Or install with: pip install playwright && playwright install chromium",
            file=sys.stderr
        )
        sys.exit(1)

    thread_id = extract_thread_id_from_url(url)
    target_clean = target_user.lower().replace("u/", "")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        qa_url = url if "sort=qa" in url else f"{url.split('?')[0]}?sort=qa"
        page.goto(qa_url, wait_until="networkidle", timeout=45000)

        for _ in range(5):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)

        title = page.title()
        post_el = page.query_selector("shreddit-post")
        created_raw = post_el.get_attribute("created-timestamp") if post_el else None
        if not created_raw:
            time_el = page.query_selector("time")
            created_raw = time_el.get_attribute("datetime") if time_el else None

        created_iso = ""
        created_utc = None
        date_str = ""
        if created_raw:
            from datetime import datetime, timezone
            try:
                # Handle varying ISO string formats e.g. 2024-05-09T16:38:51.278000+0000 or Z
                clean_raw = created_raw.replace("Z", "+00:00")
                if re.search(r'[+-]\d{4}$', clean_raw):
                    clean_raw = clean_raw[:-2] + ":" + clean_raw[-2:]
                dt = datetime.fromisoformat(clean_raw)
                created_utc = int(dt.timestamp())
                created_iso = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                date_str = dt.astimezone(timezone.utc).strftime("%b %d, %Y")
            except (ValueError, TypeError):
                pass

        raw_comments = []
        comment_nodes = page.query_selector_all("shreddit-comment")

        for node in comment_nodes:
            cid = node.get_attribute("thingid") or node.get_attribute("id") or ""
            parent_id = node.get_attribute("parentid") or ""
            author = node.get_attribute("author") or ""
            permalink = node.get_attribute("permalink") or ""
            body_el = node.query_selector("div[slot='comment']")
            body_text = body_el.inner_text().strip() if body_el else ""

            raw_comments.append({
                "id": cid,
                "parent_id": parent_id,
                "author": author,
                "body": body_text,
                "permalink": permalink
            })

        browser.close()

    items = pair_questions_and_answers(raw_comments, target_clean)

    sub_match = re.search(r'/r/([a-zA-Z0-9_]+)', url, re.IGNORECASE)
    subreddit = f"r/{sub_match.group(1)}" if sub_match else "r/Reddit"

    clean_topic = re.sub(r'\s*:\s*r/[a-zA-Z0-9_]+.*$', '', title, flags=re.IGNORECASE).strip()
    clean_topic = re.sub(r'\s*-\s*Reddit.*$', '', clean_topic, flags=re.IGNORECASE).strip()

    meta = {
        "thread_id": thread_id,
        "title": clean_topic,
        "topic": clean_topic,
        "subreddit": subreddit,
        "original_url": url,
        "created_utc": created_utc,
        "created_iso": created_iso,
        "date": date_str
    }
    return meta, items

def save_ama_archive(
    meta: dict,
    items: list[dict],
    categories: list[str],
    target_user: str,
    output_dir: str = "assets/data",
    avatar_url: str | None = None
):
    """Saves thread Q&A files and updates the registry."""
    os.makedirs(output_dir, exist_ok=True)
    thread_id = meta["thread_id"]

    target_handle = target_user.replace("u/", "").strip()
    guest_display_name = target_handle.title()
    clean_topic = meta.get("topic") or meta.get("title", f"AMA with {target_user}")
    clean_topic = re.sub(r'\s*:\s*r/[a-zA-Z0-9_]+.*$', '', clean_topic, flags=re.IGNORECASE).strip()

    fixed_title = f"{guest_display_name} AMA"
    date_str = meta.get("date", "")
    created_iso = meta.get("created_iso", "")
    created_utc = meta.get("created_utc")

    registry_path = os.path.join(output_dir, "threads.json")
    registry = []
    if os.path.exists(registry_path):
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except (json.JSONDecodeError, OSError):
            registry = []

    existing_idx = next((i for i, t in enumerate(registry) if t.get("id") == thread_id), None)

    avatar = avatar_url or meta.get("avatar_url")
    if not avatar and existing_idx is not None:
        avatar = registry[existing_idx].get("avatar_url")

    guest_info = {
        "name": guest_display_name,
        "handle": target_handle,
        "label": f"{target_handle} · u/{target_handle}"
    }
    if avatar:
        guest_info["avatar_url"] = avatar

    thread_data = {
        "thread_id": thread_id,
        "title": fixed_title,
        "topic": clean_topic,
        "date": date_str,
        "created_iso": created_iso,
        "created_utc": created_utc,
        "guest": guest_info,
        "subreddit": meta.get("subreddit", "r/Reddit"),
        "original_url": meta.get("original_url", ""),
        "categories": categories,
        "total_answers": len(items),
        "notice": "Deleted or removed answers are shown as deleted or removed.",
        "items": items
    }
    if avatar:
        thread_data["avatar_url"] = avatar

    json_path = os.path.join(output_dir, f"{thread_id}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(thread_data, f, indent=2, ensure_ascii=False)

    js_path = os.path.join(output_dir, f"{thread_id}.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(f"window.__AMA_DATA__ = {json.dumps(thread_data, indent=2, ensure_ascii=False)};\n")

    entry = {
        "id": thread_id,
        "title": fixed_title,
        "topic": clean_topic,
        "date": date_str,
        "created_iso": created_iso,
        "created_utc": created_utc,
        "guest_name": guest_display_name,
        "guest_handle": target_handle,
        "guest_label": target_handle,
        "subreddit": thread_data["subreddit"],
        "original_url": thread_data["original_url"],
        "total_answers": len(items),
        "file": f"assets/data/{thread_id}.json",
        "js_file": f"assets/data/{thread_id}.js",
        "is_default": len(registry) == 0
    }
    if avatar:
        entry["avatar_url"] = avatar

    if existing_idx is not None:
        registry[existing_idx] = entry
    else:
        registry.append(entry)

    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)

    js_registry_path = os.path.join(output_dir, "threads.js")
    with open(js_registry_path, "w", encoding="utf-8") as f:
        f.write(f"window.__AMA_THREADS__ = {json.dumps(registry, indent=2, ensure_ascii=False)};\n")

    print(f"Successfully saved {len(items)} Q&A pairs with {len(categories) - 1} categories to {json_path}")

def main():
    parser = argparse.ArgumentParser(description="Fetch and archive Reddit AMA threads by user.")
    parser.add_argument("--url", required=True, help="Reddit thread URL or ID")
    parser.add_argument("--user", required=True, help="AMA guest username (e.g. carpe02)")
    parser.add_argument("--output-dir", default="assets/data", help="Output directory for JSON/JS assets")
    parser.add_argument("--mode", choices=["auto", "api", "headless"], default="auto", help="Fetch mode")
    parser.add_argument(
        "--ai-provider",
        choices=["auto", "gemini", "anthropic", "openrouter", "openai", "groq", "deepseek", "mistral", "ollama", "generic"],
        default="auto",
        help="AI provider for dynamic topic tagging"
    )
    parser.add_argument("--api-key", help="AI API key (or set via environment variable)")
    parser.add_argument("--ai-model", help="Specific model name (e.g. claude-3-5-haiku-20241022, gpt-4o-mini, gemini-2.0-flash)")
    parser.add_argument("--ai-base-url", help="Custom base URL for OpenAI-compatible endpoint or Ollama")
    parser.add_argument("--recategorize", action="store_true", help="Force re-running AI categorization on an existing thread")
    parser.add_argument("--force", action="store_true", help="Force re-fetching an already archived thread")
    parser.add_argument("--avatar-url", help="Custom avatar image link for the AMA guest")
    args = parser.parse_args()

    thread_id = extract_thread_id_from_url(args.url)
    existing_file = os.path.join(args.output_dir, f"{thread_id}.json")
    registry_file = os.path.join(args.output_dir, "threads.json")

    is_already_archived = os.path.exists(existing_file)
    if not is_already_archived and os.path.exists(registry_file):
        try:
            with open(registry_file, "r", encoding="utf-8") as f:
                registry = json.load(f)
            is_already_archived = any(t.get("id") == thread_id for t in registry)
        except (json.JSONDecodeError, OSError):
            pass

    if is_already_archived and not (args.force or args.recategorize):
        print(f"Thread '{thread_id}' is already archived in {args.output_dir}. Skipping fetch. Pass --force to re-fetch.")
        return

    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")

    mode = args.mode
    if mode == "auto":
        mode = "api" if (client_id and client_secret) else "headless"

    is_new_thread = not is_already_archived
    should_run_ai = is_new_thread or args.recategorize

    chosen_provider, resolved_key = resolve_ai_provider_and_key(args.ai_provider, args.api_key)
    has_ai = bool(resolved_key or chosen_provider in ("ollama", "generic"))

    if should_run_ai and not has_ai:
        print(
            "Error: An AI key is required to categorize this AMA thread dynamically.\n"
            "Supported providers & keys (environment variable or --api-key):\n"
            "  - Gemini: GEMINI_API_KEY / GOOGLE_API_KEY\n"
            "  - Anthropic: ANTHROPIC_API_KEY\n"
            "  - OpenRouter: OPENROUTER_API_KEY\n"
            "  - OpenAI: OPENAI_API_KEY\n"
            "  - Groq: GROQ_API_KEY\n"
            "  - DeepSeek: DEEPSEEK_API_KEY\n"
            "  - Mistral: MISTRAL_API_KEY\n"
            "  - Local Ollama: --ai-provider ollama\n"
            "  - Generic endpoint: --ai-provider generic --ai-base-url <url>\n",
            file=sys.stderr
        )
        sys.exit(1)

    print(f"Archiving thread {thread_id} for user u/{args.user} via mode: {mode}")

    if mode == "api":
        if not client_id or not client_secret:
            print("Error: REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET required for API mode.", file=sys.stderr)
            sys.exit(1)
        meta, items = fetch_with_api(thread_id, client_id, client_secret, args.user)
    else:
        meta, items = fetch_with_headless(args.url, args.user)

    if should_run_ai or has_ai:
        categories, items = ai_categorize_items(
            items,
            provider=chosen_provider,
            api_key=resolved_key,
            model=args.ai_model,
            base_url=args.ai_base_url
        )
    else:
        # If re-running an already-categorized thread without an AI key, preserve existing categories
        with open(existing_file, "r", encoding="utf-8") as f:
            prev_data = json.load(f)
            prev_map = {str(it["id"]): it.get("category", "") for it in prev_data.get("items", [])}
            categories = prev_data.get("categories", ["All"])
            for it in items:
                it["category"] = prev_map.get(str(it["id"]), "")
                it["search_text"] = f"{it['question_text']} {it['answer_text']} {it['question_author']} {it['category']}".lower()

    save_ama_archive(meta, items, categories, args.user, args.output_dir, avatar_url=args.avatar_url)

if __name__ == "__main__":
    main()
