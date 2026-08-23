# GS Assistant -- diary and reminder tools

Gives the WhatsApp assistant on `gs-vm` the ability to put things in Gus's
diary and set reminders that make his phone go off.

## Why it works this way

The assistant runs `claude -p` with bash access, so new abilities are just
new commands plus a line in the system prompt telling it they exist. There is
no server code to change.

An alarm in the iPhone Clock app cannot be set remotely -- Apple exposes no
such API. A calendar event with a popup alert does the same job, because the
phone is already synced to that calendar. So reminders are short calendar
entries marked "free" so they do not clutter the day.

## Install

On the VM:

    git clone https://github.com/gselectrical/gus.git ~/gus-tools
    bash ~/gus-tools/assistant/install.sh

It builds its own virtualenv at `~/gs-app/.venv-assistant`, so the Python the
running services use is left untouched. Three commands land on PATH:

| Command | What it does |
| --- | --- |
| `gs-agenda` | what's on today, or `--days 7` for the week |
| `gs-diary` | add a job or appointment |
| `gs-remind` | set a reminder |

## Credentials

`gs_google.py` looks for Google credentials the machine already has --
`~/gs-app/token.json`, a service account, or application default credentials.
To see what it found:

    ~/gs-app/.venv-assistant/bin/python ~/gs-app/scripts/gs_google.py

If nothing turns up, authorise once:

    ~/gs-app/.venv-assistant/bin/python ~/gs-app/scripts/gs_google.py --authorise

Writing to the diary needs the `calendar` scope. Read-only credentials will
list events but fail on `gs-diary` -- the error says so rather than failing
silently.

## Wiring it into the assistant

Copy the text in `PROMPT_ADDITIONS.md` into `SYSTEM_PROMPT` in
`~/gs-app/scripts/meta_whatsapp_webhook.py`, then:

    sudo systemctl restart meta-whatsapp-webhook whatsapp-bot

## Checking the time parser

`timeparse.py` runs standalone, which is the quickest way to confirm it reads
phrasing the way you expect:

    python3 ~/gs-app/scripts/timeparse.py "thursday 2pm" "in 40m" "25/08 09:00"
