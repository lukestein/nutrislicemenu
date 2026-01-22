A small tool to send a push notification with tomorrow's school lunch menu.

Uses github actions and [ntfy](https://ntfy.sh/).

## Features

- **Nutrislice Menus** (`nutrislicemenu.py`): Fetches lunch menus from Nutrislice API
- **Dine On Campus Menus** (`dineoncampus.py`): Fetches lunch menus from Dine On Campus websites

## Configuration

Both scripts use environment variables for configuration:

- `NTFY_TOPIC_STUB`: Topic stub for Nutrislice notifications (set via GitHub Actions secrets)
- `NTFY_TOPIC_STUB_DOC`: Topic stub for Dine On Campus notifications (set via GitHub Actions secrets)

## Running Locally

Install dependencies:
```bash
pip install -r requirements.txt
```

Run Nutrislice menu:
```bash
python nutrislicemenu.py
```

Run Dine On Campus menu:
```bash
python dineoncampus.py
```
