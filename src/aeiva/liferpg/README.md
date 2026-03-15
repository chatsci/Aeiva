# LifeRPG

## Overview

LifeRPG is Aeiva's structured user life model.

It is designed for a human-centered agent whose long-term purpose is not only to answer questions or automate tasks, but to help a person grow with more clarity, agency, and continuity over time.

The name "LifeRPG" is intentional. It borrows the spirit of role-playing games not to reduce life into a toy, but to make growth legible, motivating, and operational:

- a person has an evolving identity
- a person plays multiple roles
- each role develops through concrete work and achievements
- projects and commitments define long-range direction
- TODOs translate direction into executable focus

In that sense, LifeRPG is a shared panel for both the human and the agent:

- for the human, it provides a coherent view of self, growth, and ongoing work
- for the agent, it provides a stable structure for understanding who the user is, what matters, and how to support that person over time

## Design Goals

LifeRPG exists to support five goals.

### 1. Make the User Model Actionable

The agent should not only remember isolated facts. It should understand a person's identity, roles, artifacts, projects, and active commitments in a form that can guide real decisions.

### 2. Support Human Growth Rather Than Pure Automation

Aeiva is meant to augment the human, not replace the human. LifeRPG therefore emphasizes growth surfaces:

- roles that can mature
- inventory that reflects concrete outputs
- projects that define direction
- TODO horizons that support execution

### 3. Preserve Conceptual Clarity

LifeRPG is not a generic memory dump. It is a structured model of:

- who the user is
- what the user carries
- what the user is working on

This boundary is deliberate. Long-form conversation history belongs to memory. LifeRPG is the organized life panel built on top of more raw memory traces.

### 4. Stay Lightweight and Maintainable

The schema avoids excessive field explosion. Most information is represented in natural language, with only a small amount of bounded structure where structure genuinely helps:

- role levels use `L1` to `L5`
- radar views use profession templates
- TODOs use explicit status and deadline fields

The intent is to avoid false precision and reduce maintenance burden.

### 5. Remain Decoupled

LifeRPG is implemented as its own module and store. It can read context from memory outputs, but it is not embedded inside memory and does not require tight cross-module coupling to exist.

## Core Philosophy

### Life as an Organized Growth Surface

LifeRPG models a human life as a structured but open-ended game of development.

The metaphor matters because it gives the system a language for:

- progression without crude gamification
- meaningful feedback without reducing everything to scores
- continuity across many projects and life chapters
- motivation through visible growth and accumulated artifacts

The point is not to force life into a game mechanic. The point is to give growth a panel that is easier to reason about than an unstructured memory archive.

### Language First, Metrics Second

Many aspects of human life should not be quantified aggressively. LifeRPG therefore prefers:

- natural-language descriptions for identity, commitments, control, character, condition, and context
- low-cardinality levels only where bounded progression is useful
- profession-specific radar templates instead of arbitrary psychometric dimensions

This keeps the model more interpretable and less brittle.

### Roles, Not Abstract Skill Clouds

LifeRPG organizes growth primarily through roles such as:

- Researcher
- Programmer
- AI Engineer

This is more intuitive than a flat skill inventory because people usually experience growth through social and professional roles rather than isolated capability atoms.

Each role can carry:

- a short description
- an overall level
- a radar view with template-backed dimensions
- concrete achievements

### Inventory Should Mean Concrete Outputs

Inventory is not a bag of random facts. It is meant to represent the concrete artifacts a role accumulates:

- papers
- projects
- prototypes
- tools
- notable outputs
- important bugs fixed or systems delivered

The design principle is simple: inventory should make a person feel the weight of what they have actually built, not what the system vaguely thinks they might be good at.

## What LifeRPG Stores

The current schema is intentionally compact.

### 1. User

Stable user-facing profile information:

- bio
- identity
- commitments
- control
- character

### 2. State

A lightweight current-state layer:

- condition
- context

This is not turn-by-turn state. It is a higher-level operating snapshot.

### 3. Roles

A list of active roles. Each role includes:

- `name`
- `description`
- `level`
- `radar`
- `achievements`

### 4. Inventory

Inventory is organized as `role_bags`, so artifacts stay attached to the roles that make them meaningful.

### 5. Projects

Projects are the main long-horizon execution objects. They represent major directions in a person's life and work.

Each project currently includes:

- `title`
- `description`
- `milestones`
- `deadline`
- `status`

### 6. TODOs

TODOs are grouped by horizon:

- `year`
- `month`
- `week`
- `day`

This gives the agent and the human a simple progression bridge from strategic direction to near-term execution.

## What LifeRPG Explicitly Avoids

LifeRPG is intentionally not:

- a full autobiographical memory log
- a psychological diagnosis engine
- a dense numeric scoring system
- a surveillance dashboard
- a rigid planner that dictates the user's life

It also avoids arbitrary field proliferation. If a field does not clearly improve self-understanding, agent support, or execution clarity, it does not belong here.

## Relation to Human-Centered Agent Design

LifeRPG fits Aeiva's human-centered direction in three ways.

### 1. It supports long-horizon personalization

The agent can adapt not only to recent turns, but to a more stable model of the person's life trajectory.

### 2. It supports growth-aware assistance

The agent can choose support strategies that help the person learn, build, and mature rather than simply offloading everything.

### 3. It supports coherent multi-role identity

A human is not only "a user". A human is often simultaneously a researcher, builder, friend, family member, manager, or artist. LifeRPG gives the agent a way to hold that plurality cleanly.

More broadly, the module is compatible with a human-centered framing in which a person can be understood across multiple layers:

- relatively stable identity and commitments
- evolving roles and capabilities
- active projects and current execution horizons

That layered view is one reason LifeRPG is useful: it turns human-centered theory into a practical, inspectable interface.

## Update Principles

LifeRPG follows a simple update philosophy.

### Session and Period Reviews

The profile is not meant to update every turn. Instead, it is updated on slower cycles:

- session
- daily
- weekly
- monthly
- yearly

This makes the system more stable and avoids overfitting LifeRPG to transient dialogue noise.

### Minimal Patch Updates

When an update is needed, the system prefers a minimal merge patch rather than rewriting the whole profile. This preserves stability and keeps updates easier to audit.

### Objective Before Speculative

The model should prefer updates grounded in observable context:

- explicit self-descriptions
- concrete projects
- visible artifacts
- active deadlines
- recurring patterns stable enough to matter

It should avoid inventing private facts or over-interpreting weak signals.

## Current Implementation Notes

The current module includes:

- a dedicated store
- a schema normalizer
- a neuron for update orchestration
- a standalone LifeRPG web panel

The panel is currently designed as a clean dashboard for:

- overview
- roles
- inventory
- projects
- TODOs

Radar views are template-based and intentionally limited to a small number of profession types. The guiding principle is: if no trustworthy template exists, prefer text over fake precision.

## Non-Goals

LifeRPG should not become:

- a bloated ontology
- an over-automated self-help system
- a generic KPI dashboard
- a substitute for human judgment

Its job is narrower and more valuable:

to provide Aeiva with a clean, motivating, and durable model of the user's life world, growth surfaces, and active commitments.

## Summary

LifeRPG is Aeiva's answer to a simple question:

How should a human-centered agent represent a person's life in a way that is structured enough to guide support, but open enough to respect the richness of being human?

The answer is not raw memory alone, and it is not arbitrary scoring.

The answer here is a compact life panel built around:

- identity
- roles
- inventory
- projects
- TODO horizons

That is the core of LifeRPG.
