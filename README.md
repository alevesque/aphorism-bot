# Aphorism Bot

Daily aphorisms posted to a Telegram group.

## Setup

### 1. Install dependencies

```
pip install -r requirements.txt
```

### 2. Create your bot

1. Open Telegram, talk to **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the API token into `config.json` -> `bot_token`
   (already pre-filled if you gave it to Claude Code)

### 3. Get the group chat ID

Add your bot to the target group, then send a message in the group.
Run this once to find the chat ID:

```bash
python -c "import urllib.request,json; r=urllib.request.urlopen('https://api.telegram.org/bot<TOKEN>/getUpdates'); print(json.dumps(json.load(r), indent=2))"
```

Look for `"id"` inside `"chat"` in the output.
Paste that negative number as the `chat_id` in `config.json`.

### 4. Edit config.json

```json
{
  "bot_token":          "000:AB123...",
  "chat_id":            "-000...",
  "post_hour":          8,
  "post_minute":        0,
  "timezone":           "America/Los_Angeles",
  "enabled_authors":    [],
  "anthropic_api_key":  "sk-ant-...",
  "request_model":      "claude-haiku-4-5"
}
```

- `post_hour` / `post_minute`: when to post each day (24-hour clock)
- `timezone`: any pytz timezone string (e.g. `UTC`, `America/New_York`)
- `enabled_authors`: list of author names to include, e.g. `["Oscar Wilde", "Nietzsche"]`.
  Leave as `[]` to include **all** authors.
- `anthropic_api_key`: your Anthropic API key — required only for the `/request` command.
- `request_model`: Claude model used by `/request` (default: `claude-haiku-4-5`).

### 5. Run the bot

```bash
python aphorism_bot.py
```

Keep it running (e.g. with `screen`, `tmux`, or a system service) so the daily job fires.

## Commands

| Command | Description |
|---|---|
| `/aphorism` | Get a random quote immediately |
| `/authors` | List all authors and quote counts |
| `/request <author>` | Look up and add quotes from an author via Claude AI |
| `/help` | Show help |

## Adding quotes

**Via bot command (easiest):**

```
/request Mary Shelley
```

The bot calls Claude AI to fetch 10 new quotes and appends them to `quotes.json`.
Running `/request` again for the same author fetches additional quotes.

**Manually:** open `quotes.json` and append new entries following the schema:

```json
{
  "id": 116,
  "author": "Author Name",
  "text": "The quote text goes here.",
  "source": "Title of Work"
}
```

`source` can be `null` if unknown. The bot tracks used quote IDs in `used_quotes.json`
so it cycles through the full pool before repeating.

## Timezone reference

| Region | Timezone string |
|---|---|
| UTC | `UTC` |
| US Eastern | `America/New_York` |
| US Central | `America/Chicago` |
| US Mountain | `America/Denver` |
| US Pacific | `America/Los_Angeles` |
| London | `Europe/London` |
| Paris / Berlin | `Europe/Paris` |
| Moscow | `Europe/Moscow` |
| Tokyo | `Asia/Tokyo` |
| Sydney | `Australia/Sydney` |
