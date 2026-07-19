# Aster documentation

This directory is the canonical documentation for installing, operating, using, and extending Aster.

The root [README](../README.md) is intentionally short. Detailed procedures and reference material belong here.

## Start here

- [Installation](guides/installation.md) — bundled or external PostgreSQL, first setup, networking, and upgrades.
- [Configuration](guides/configuration.md) — model roles, endpoints, personas, tools, retrieval, and secrets.
- [Core workspaces](guides/core-workspaces.md) — chat, images, automations, communications, agents, and settings.
- [Backup and upgrade](guides/backup-and-upgrade.md) — database, media, restore, and migration procedures.
- [Development](guides/development.md) — repository layout, local checks, CI, and contribution workflow.

## Feature guides

- [Communication Hub](guides/communication-hub.md)
- [Autonomous agents](guides/autonomous-agents.md)

## Reference

- [Architecture](reference/architecture.md)
- [Environment variables](reference/environment.md)
- [Security](reference/security.md)

Reference documents describe the current implementation. When behavior changes, update the reference in the same commit.

## Product

- [Project charter](product/project-charter.md)
- [Roadmap](product/roadmap.md)

The charter records stable product principles. The roadmap records current direction without promising speculative stages.

## Architecture decisions

- [ADR index](decisions/README.md)

ADRs explain why durable architectural choices were made. Accepted records are historical documents and are not silently rewritten to describe newer behavior.

## Archive

- [Implementation archive](archive/README.md)

The archive contains completed stage plans, interface checklists, and rollout notes. These files are useful history, but they are not current operating instructions.

## Repository map

```text
apps/
  api/                  FastAPI application, worker runtime, tests, and migrations
  web/                  Next.js application
docs/
  guides/               task-oriented procedures
  reference/            current technical contracts
  product/              vision and direction
  decisions/            architecture decision records
  archive/              completed implementation records
scripts/ci/              full-stack contract checks
.github/workflows/       active GitHub Actions workflows
compose.yaml             default self-hosted stack
.env.example             documented runtime configuration
```

## Documentation rules

1. Keep the root README concise.
2. Put procedures in `guides/` and stable contracts in `reference/`.
3. Keep product intent separate from implementation instructions.
4. Move completed checklists and stage plans to `archive/`.
5. Never include real credentials, private endpoints, personal identities, or provider-specific secrets.
6. Use relative links so documentation works in forks and local checkouts.
7. Update examples when routes, service names, migrations, or environment variables change.
