# Retirement Planning v2

**Focused retirement planning tool built on proven budgy architecture**

## Project Vision

This project builds a web-based retirement planning application that helps forecast retirement readiness by analyzing current expenses, projecting post-retirement needs, and running "what if" scenarios.

**Core Goal**: Answer "When can I retire?" using current net worth, estimated expenses, and passive income to forecast savings depletion.

**Target Retirement**: No sooner than Father's Day 2027 (subject to change)

## Architecture Strategy

### Phase 1: Foundation (Port from Budgy)
- **OFX Import System**: Proven importer from `/Users/mark/git/budgy/src/budgy/core/importer.py`
- **Database Layer**: Retirement-focused schema from `/Users/mark/git/budgy/src/budgy/core/database.py`
- **Expense Categorization**: Leverage budgy's expense_type system (recurring vs one-time)

### Phase 2: Web Interface
- **Desktop-focused design**: Target 1024px+ screens, no mobile support
- **Retirement-specific views**: Not generic transaction tables, but retirement analysis dashboards
- **Technology choices**: TBD based on Phase 1 requirements

### Phase 3: Forecasting Engine
- **Savings depletion modeling**: Core retirement planning calculations
- **Scenario analysis**: "What if" modeling for different retirement dates/expenses
- **Passive income integration**: Factor in investment income streams

## Key Design Principles

1. **Retirement-first**: Every feature serves retirement planning, not general budgeting
2. **Proven components**: Reuse working budgy architecture where applicable
3. **Web-based**: Modern interface replacing budgy's pygame GUI
4. **Security-conscious**: Encrypt financial data, secure OFX handling
5. **Desktop-focused**: No mobile/tablet support planned

## Legacy Integration

**Source project**: `/Users/mark/git/budgy` contains:
- Mature OFX processing with duplicate detection
- Retirement-focused expense categorization
- Robust database schema with migration support
- Comprehensive test suite

**Migration strategy**: Port proven components, enhance for web, add forecasting capabilities.

## Development Approach

- **Start simple**: Basic OFX import and expense categorization first
- **Iterative enhancement**: Add complexity (inflation modeling, scenario analysis) later
- **Claude-driven development**: Leverage improved AI collaboration skills
- **Clear requirements**: Specific, focused requests to prevent scope drift

## Getting Started

This project is designed for development with Claude Code. When starting:

1. **Define specific Phase 1 goals**: What exact functionality from budgy to port first
2. **Choose technology stack**: Based on actual requirements, not assumptions
3. **Set up development environment**: Testing, linting, project structure
4. **Implement incrementally**: Small, focused changes with clear objectives

## Security Requirements

- Encrypt OFX files after import
- Secure database storage for financial data
- No secrets in version control
- Preserve historical data for regeneration

---

**Note**: This project replaces the original retirement-planning project which suffered from scope drift and contradictory documentation. This v2 starts fresh with clear focus and improved development practices.