# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Retirement Planning v2 is a web-based application for retirement forecasting that builds on proven budgy architecture. The project focuses on answering "When can I retire?" through expense analysis, net worth tracking, and savings depletion modeling.

**Target Retirement**: Father's Day 2027 (subject to change)

## Development Status

This is an early-stage project in the initial setup phase. The codebase currently contains only project documentation and setup files.

## Architecture Strategy

### Three-Phase Development:
1. **Phase 1: Foundation** - Port OFX import system, database layer, and expense categorization from `/Users/mark/git/budgy`
2. **Phase 2: Web Interface** - Desktop-focused design (1024px+), retirement-specific dashboards
3. **Phase 3: Forecasting Engine** - Savings depletion modeling and scenario analysis

### Legacy Integration
- **Source project**: `/Users/mark/git/budgy` contains mature components to port:
  - OFX processing with duplicate detection (`/Users/mark/git/budgy/src/budgy/core/importer.py`)
  - Retirement-focused expense categorization
  - Database schema with migrations (`/Users/mark/git/budgy/src/budgy/core/database.py`)
  - Comprehensive test suite

## Key Design Principles

1. **Retirement-first**: Every feature serves retirement planning, not general budgeting
2. **Proven components**: Reuse working budgy architecture where applicable  
3. **Web-based**: Modern interface replacing budgy's pygame GUI
4. **Security-conscious**: Encrypt financial data, secure OFX handling
5. **Desktop-focused**: No mobile/tablet support planned

## Security Requirements

- Encrypt OFX files after import
- Secure database storage for financial data
- No secrets in version control
- Preserve historical data for regeneration

## Development Environment

This project uses Python (indicated by .gitignore) and follows standard Python project structure. No build system, testing framework, or dependency management is currently configured.

## Development Approach

- Start with Phase 1: basic OFX import and expense categorization
- Implement incrementally with small, focused changes
- Define technology stack based on actual requirements
- Leverage Claude Code for development collaboration
- Clear requirements to prevent scope drift (learned from v1 project failure)

## Important Notes

- This v2 project replaces the original retirement-planning project which suffered from scope drift
- Project is designed specifically for Claude Code development workflow
- Focus on specific, actionable requirements rather than generic development practices