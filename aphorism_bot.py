#!/usr/bin/env python3
"""
Aphorism Bot -- daily wisdom from antinomian and morally provocative thinkers.

Commands:
  /aphorism        -- deliver a quote on demand
  /authors         -- list all authors in the database
  /request <name>  -- look up and add quotes from an author via Claude AI
  /help            -- show help
"""

import json
import logging
import random
from pathlib import Path
from datetime import time as dt_time

import anthropic
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BASE_DIR    = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
QUOTES_PATH = BASE_DIR / "quotes.json"
USED_PATH   = BASE_DIR / "used_quotes.json"


# -- helpers ------------------------------------------------------------------

def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def pick_quote(config: dict, quotes: list, used: list) -> dict:
    enabled = set(config.get("enabled_authors", []))
    pool = [q for q in quotes if not enabled or q["author"] in enabled]
    if not pool:
        raise ValueError("No quotes found. Check enabled_authors in config.json.")
    unused = [q for q in pool if q["id"] not in used]
    if not unused:
        used.clear()
        unused = pool
    quote = random.choice(unused)
    used.append(quote["id"])
    return quote


def format_quote(quote: dict) -> str:
    src = quote.get("source") or ""
    source_tag = f"  [{src}]" if src else ""
    text   = quote["text"]
    author = quote["author"]
    return f"\u201c{text}\u201d\n\n\u2014 {author}{source_tag}"


# -- Claude API quote fetcher -------------------------------------------------

async def fetch_quotes_from_claude(
    author: str,
    existing_texts: list,
    api_key: str,
    model: str,
    count: int = 10,
) -> list:
    """Ask Claude for authentic quotes from the given author."""
    existing_block = (
        "\n".join(f"- {t}" for t in existing_texts[:40])
        if existing_texts else "(none yet)"
    )
    prompt = (
        f"Provide {count} authentic, verifiable quotes attributed to {author}.\n\n"
        'Return ONLY a JSON object -- no markdown fences, no explanations -- '
        'using exactly this structure:\n'
        '{"quotes": [{"text": "quote text", "source": "work title or null"}, ...]}\n\n'
        "Rules:\n"
        f"- All quotes must be genuinely attributed to {author}\n"
        "- Each quote must differ from those already in the database (listed below)\n"
        "- Include the source work where known; otherwise use null\n"
        "- Vary the themes across the selection\n\n"
        f"Already in database for {author} (do not repeat):\n{existing_block}"
    )

    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = next((b.text for b in response.content if b.type == "text"), "")
    stripped = raw.strip()
    # Strip markdown code fences if the model wraps the JSON anyway.
    # Use chr(96)*3 so backticks don't trigger shell command-substitution.
    fence = chr(96) * 3
    if stripped.startswith(fence):
        stripped = stripped.split("\n", 1)[1].rsplit(fence, 1)[0].strip()

    data = json.loads(stripped)
    return data.get("quotes", [])


# -- scheduled job ------------------------------------------------------------

async def daily_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_json(CONFIG_PATH)
    quotes = load_json(QUOTES_PATH)
    used   = load_json(USED_PATH) if USED_PATH.exists() else []
    quote  = pick_quote(config, quotes, used)
    save_json(USED_PATH, used)
    await context.bot.send_message(chat_id=config["chat_id"], text=format_quote(quote))
    logger.info("Posted quote #%s by %s", quote["id"], quote["author"])


# -- standard command handlers ------------------------------------------------

async def cmd_aphorism(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = load_json(CONFIG_PATH)
    quotes = load_json(QUOTES_PATH)
    used   = load_json(USED_PATH) if USED_PATH.exists() else []
    quote  = pick_quote(config, quotes, used)
    save_json(USED_PATH, used)
    await update.message.reply_text(format_quote(quote))


async def cmd_authors(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    quotes  = load_json(QUOTES_PATH)
    authors = sorted({q["author"] for q in quotes})
    count   = {a: sum(1 for q in quotes if q["author"] == a) for a in authors}
    lines   = [f"  \u2022 {a}  ({count[a]})" for a in authors]
    await update.message.reply_text("Authors in database:\n" + "\n".join(lines))


async def cmd_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Look up quotes from an author via Claude and append them to quotes.json."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /request <author name>\nExample: /request Albert Camus"
        )
        return

    author     = " ".join(context.args).strip()
    status_msg = await update.message.reply_text(
        f"Searching for quotes from {author}\u2026"
    )

    try:
        config  = load_json(CONFIG_PATH)
        api_key = config.get("anthropic_api_key", "")
        if not api_key or api_key == "YOUR_ANTHROPIC_API_KEY":
            await status_msg.edit_text(
                "Add your Anthropic API key as anthropic_api_key in config.json "
                "to use /request."
            )
            return

        model  = config.get("request_model", "claude-haiku-4-5")
        quotes = load_json(QUOTES_PATH)

        # Preserve existing capitalisation for known authors
        author_map = {q["author"].lower(): q["author"] for q in quotes}
        canonical  = author_map.get(author.lower(), author)

        existing_texts = [
            q["text"] for q in quotes if q["author"].lower() == author.lower()
        ]
        existing_count = len(existing_texts)

        new_quotes = await fetch_quotes_from_claude(
            canonical, existing_texts, api_key, model
        )

        if not new_quotes:
            await status_msg.edit_text(
                f"No quotes returned for {canonical}. "
                "Try a different spelling or author name."
            )
            return

        # Deduplicate against what is already stored
        existing_lower = {t.lower() for t in existing_texts}
        fresh = [
            q for q in new_quotes
            if q.get("text", "").lower() not in existing_lower
        ]

        if not fresh:
            await status_msg.edit_text(
                f"All returned quotes for {canonical} are already in the database."
            )
            return

        next_id = max((q["id"] for q in quotes), default=0) + 1
        added   = []
        for q in fresh:
            entry = {
                "id":     next_id,
                "author": canonical,
                "text":   q["text"].strip(),
                "source": q.get("source") or None,
            }
            quotes.append(entry)
            added.append(entry)
            next_id += 1

        save_json(QUOTES_PATH, quotes)
        logger.info(
            "Added %d quotes from %s (database now %d total)",
            len(added), canonical, len(quotes),
        )

        preview_lines = []
        for q in added[:3]:
            snippet = q["text"][:90] + ("\u2026" if len(q["text"]) > 90 else "")
            preview_lines.append(f"\u201c{snippet}\u201d")
        preview = "\n".join(preview_lines)
        tail    = f"\n\u2026and {len(added) - 3} more." if len(added) > 3 else ""
        reply   = (
            f"Added {len(added)} quotes from {canonical} "
            f"({existing_count} already existed).\n\n{preview}{tail}"
        )
        await status_msg.edit_text(reply)

    except json.JSONDecodeError as exc:
        logger.error("JSON parse error in /request: %s", exc)
        await status_msg.edit_text(
            "Claude returned an unexpected format. Please try again."
        )
    except anthropic.AuthenticationError:
        await status_msg.edit_text(
            "Invalid Anthropic API key. Check anthropic_api_key in config.json."
        )
    except anthropic.RateLimitError:
        await status_msg.edit_text("Rate limit hit. Please wait and try again.")
    except Exception as exc:
        logger.error("Error in /request: %s", exc, exc_info=True)
        await status_msg.edit_text(f"Error: {exc}")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/aphorism          \u2014 deliver a quote on demand\n"
        "/authors           \u2014 list all authors in the database\n"
        "/request <author>  \u2014 add quotes from a new or existing author\n"
        "/help              \u2014 show this message\n\n"
        "A fresh aphorism is posted automatically every day at the time "
        "configured in config.json."
    )


# -- main ---------------------------------------------------------------------

def main() -> None:
    config = load_json(CONFIG_PATH)
    token  = config["bot_token"]
    tz     = pytz.timezone(config.get("timezone", "UTC"))
    post_time = dt_time(
        hour=config.get("post_hour", 8),
        minute=config.get("post_minute", 0),
        tzinfo=tz,
    )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("aphorism", cmd_aphorism))
    app.add_handler(CommandHandler("authors",  cmd_authors))
    app.add_handler(CommandHandler("request",  cmd_request))
    app.add_handler(CommandHandler("help",     cmd_help))

    app.job_queue.run_daily(daily_post, time=post_time, name="daily_aphorism")
    logger.info(
        "Bot started. Daily post at %02d:%02d %s",
        config.get("post_hour", 8),
        config.get("post_minute", 0),
        config.get("timezone", "UTC"),
    )
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
