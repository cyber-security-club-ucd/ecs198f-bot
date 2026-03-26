# ECS 198F Discord Bot

A Discord bot that lets students authenticate with their Authentik account on
`auth.daviscybersec.org` and automatically receive the `ecs198f-student` Discord role.

## Quick Install (using UV)

```bash
git clone <repo-url>
cd ecs198f-bot
./scripts/install.sh
```

The script will:
1. Verify Python 3.12+ is available
2. Install [UV](https://docs.astral.sh/uv/) if not already present
3. Run `uv sync` to create `.venv/` with all dependencies
4. Copy `.env.example` → `.env` if no `.env` exists

After running the script, edit `.env` with your credentials.

## Manual Install

```bash
# Install UV (if not already installed)
pip install uv

# Install dependencies
uv sync

# Copy and edit environment config
cp .env.example .env
```

## How it works

1. The bot posts a persistent **Authenticate** button to the configured Discord channel.
2. A student clicks the button and receives an ephemeral message with a one-time link.
3. The link redirects to the Django web app, which starts an OAuth flow with Authentik.
4. After successful login the app checks the student's Authentik groups.
5. If the student belongs to the `198F-student` group, the app queues a Discord task.
6. The bot's queue processor picks up the task and assigns the Discord role.

## Configuration

Edit `.env` with the following values:

| Variable | Description |
|---|---|
| `DISCORD_BOT_TOKEN` | Bot token from Discord Developer Portal |
| `DISCORD_GUILD_ID` | Guild (server) ID where the bot operates |
| `ECS198F_AUTH_CHANNEL_ID` | Channel where the Authenticate button is posted |
| `ECS198F_STUDENT_ROLE_ID` | Discord role ID to assign to verified students |
| `AUTHENTIK_URL` | Authentik server URL (default: `https://auth.daviscybersec.org`) |
| `AUTHENTIK_CLIENT_ID` | OAuth2 client ID from the Authentik application |
| `AUTHENTIK_SECRET` | OAuth2 client secret |

## Running

```bash
docker compose up -d
```

## Testing

```bash
# Start the test database
docker compose -f docker-compose.test.yml up -d --wait

# Run all tests
.venv/bin/python -m pytest
```
