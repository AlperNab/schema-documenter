# schema-documenter

> **Database schema → complete auto-generated documentation.** Table descriptions, column docs, Mermaid ERD, sample queries, data dictionary, quality observations. Exports to Markdown.

[![PyPI](https://img.shields.io/pypi/v/schema-documenter?style=flat)](https://pypi.org/project/schema-documenter/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Quickstart

```bash
pip install schema-documenter
python -m schema_documenter schema.sql --markdown docs/database.md
python -m schema_documenter schema.sql --json
```

## What's generated

- **Table docs** — business description, column-by-column explanations
- **Mermaid ERD** — paste into any Mermaid renderer or GitHub README
- **Common queries** — sample SQL per table for likely access patterns
- **Data dictionary** — business terms mapped to schema
- **Sample queries** — 5-10 practical queries across multiple tables
- **Quality observations** — missing indexes, naming inconsistencies, denormalization
- **API hints** — suggested REST endpoints from the schema structure

Supports: PostgreSQL, MySQL, SQLite, MSSQL, Oracle DDL
