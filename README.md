# Aphorism Bot

Daily aphorisms posted to a Telegram group, drawn from antinomian and morally provocative thinkers.

## Authors included (115 quotes)

| Author | Quotes |
|---|---|
| Oscar Wilde | 16 |
| Niccolo Machiavelli | 12 |
| Anton LaVey | 12 |
| Friedrich Nietzsche | 16 |
| Aleister Crowley | 9 |
| Marquis de Sade | 7 |
| H. L. Mencken | 8 |
| Voltaire | 9 |
| Ambrose Bierce | 8 |
| Charles Baudelaire | 6 |
| Max Stirner | 6 |
| Lord Byron | 6 |

> **Note on James Mason:** You listed James Mason among your requested authors.
> The British actor James Mason (1909-1984) is not known for philosophical aphorisms.
> If you meant a different author, add their quotes directly to  following the existing format.

## Setup

### 1. Install dependencies



### 2. Create your bot

1. Open Telegram, talk to **@BotFather**
2. Send  and follow the prompts
3. Copy the API token into  -> 
   (already pre-filled if you gave it to Claude Code)

### 3. Get the group chat ID

Add your bot to the target group, then send a message in the group.
Run this once to find the chat ID:



Look for  in the output.
Paste that negative number as the  in .

### 4. Edit config.json



-  / : when to post each day (24-hour clock)
- : any pytz timezone string (e.g. , )
- : list of author names to include, e.g. .
  Leave as  to include **all** authors.

### 5. Run the bot



Keep it running (e.g. with , , or a system service) so the daily job fires.

## Commands

| Command | Description |
|---|---|
|  | Get a random quote immediately |
|  | List all authors and quote counts |
|  | Show help |

## Adding quotes

Open  and append new entries following the schema:



 can be  if unknown. The bot tracks used quote IDs in 
so it cycles through the full pool before repeating.
