# ECS 198F Discord Bot

A Discord bot that lets students authenticate with their Authentik account on
`auth.daviscybersec.org` and automatically receive the `ecs198f-student` Discord role.

## How it works

1. The bot posts a persistent **Authenticate** button to the configured Discord channel.
2. A student clicks the button and receives an ephemeral message with a one-time link.
3. The link redirects to the Django web app, which starts an OAuth flow with Authentik
   (`auth.daviscybersec.org`).
4. After successful login the app checks the student's Authentik groups.
5. If the student belongs to the `198F-student` group, the app queues an
   `assign_group_roles` Discord task.
6. The bot's queue processor picks up the task and calls `member.add_roles()` with the
   mapped Discord role.

## Configuration

Copy `.env.example` to `.env` and fill in the values:

| Variable | Description |
|---|---|
| `DISCORD_BOT_TOKEN` | Bot token from Discord Developer Portal |
| `DISCORD_GUILD_ID` | Guild (server) ID where the bot operates |
| `ECS198F_AUTH_CHANNEL_ID` | Channel where the Authenticate button is posted |
| `ECS198F_STUDENT_ROLE_ID` | Discord role ID to assign to verified students |
| `AUTHENTIK_URL` | Base URL of your Authentik server (default: `https://auth.daviscybersec.org`) |
| `AUTHENTIK_CLIENT_ID` | OAuth2 client ID from the Authentik application |
| `AUTHENTIK_SECRET` | OAuth2 client secret |

## Running

```bash
docker compose up -d
```

## Testing

```bash
docker compose -f docker-compose.test.yml up -d --wait
cd web && python -m pytest ../bot/tests ../web/core/tests ../web/team/tests
```
