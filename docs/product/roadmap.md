# Aster roadmap

## Current state

The core product foundation is complete:

- single-owner authentication;
- OpenAI-compatible model configuration and explicit model roles;
- persistent chat, personas, tools, memory, retrieval, and images;
- durable automations and external integrations;
- private IMAP and Discord communications;
- bounded persistent agents;
- unified desktop and mobile navigation;
- floating workspaces, command palette, and progressive settings.

## Current focus

Work is selected from real usage and deployment feedback.

The immediate priorities are:

1. improve interaction quality and consistency in daily chat workflows;
2. simplify repository structure and keep documentation current;
3. remove obsolete rollout machinery and dead implementation artifacts;
4. harden existing features before expanding the product surface;
5. improve recovery, diagnostics, and operator guidance where real failures expose gaps.

## Selection rule

A new product area should not be scheduled because it is fashionable or technically possible.

It should begin only when:

- the owner workflow is concrete;
- existing workspaces cannot solve it cleanly;
- authority and data boundaries are understood;
- the maintenance cost is acceptable for a self-hosted project;
- the change can be tested and operated without hidden infrastructure.

## Explicitly unscheduled

The following remain intentionally unscheduled:

- detailed usage and billing dashboards;
- automatic latency- or cost-based model routing;
- speculative portability layers;
- arbitrary workflow graphs;
- public sharing and social features;
- broad provider catalogs without a concrete integration need;
- multi-user tenancy;
- unrestricted browser automation or web crawling.

Completed rollout notes and interface checklists live in [`docs/archive`](../archive/README.md).
