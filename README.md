# airgap-stats

A toolkit for doing statistical analysis with an AI coding agent — Claude Code, Codex, or OpenCode — without the real dataset ever reaching the AI.

## What it is

`airgap-stats` is intended to support a privacy-preserving workflow for statistical analysis:

- the real dataset stays inside your controlled environment
- an AI coding agent helps write and refine the analysis code
- only safe, non-sensitive outputs are shared with the agent

## Core idea

Instead of exposing raw records to an AI system, you use the toolkit to:

1. run analysis steps locally against the real data
2. generate sanitized summaries, aggregates, and validation output
3. share only those derived results with the AI agent for iteration
4. keep the source dataset fully air-gapped from the model

## Intended agent support

The workflow is designed to work with AI coding agents such as:

- Claude Code
- Codex
- OpenCode

## Goal

Make it practical to combine:

- strong data handling boundaries
- reproducible statistical analysis
- fast iteration with AI-assisted coding
