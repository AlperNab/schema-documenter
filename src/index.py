#!/usr/bin/env python3
"""
schema-documenter — database schema → auto-generated docs
Produces: table descriptions, column docs, relationship diagrams (Mermaid),
sample queries, data dictionary, API spec hints, OpenAPI schema
"""
import anthropic, json, re, sys
from pathlib import Path

SYSTEM = """You are a senior database architect and technical writer.
Generate comprehensive, useful documentation from this database schema.

Make it practical — include sample queries developers will actually run,
explain the business purpose of each table, not just the technical structure.

Return ONLY valid JSON — no markdown, no explanation.

{
  "database_name": "string or 'database'",
  "dialect": "postgresql|mysql|sqlite|mssql|oracle|unknown",
  "schema_summary": "2-3 sentence description of what this database is for",
  "tables": [
    {
      "name": "table name",
      "description": "what this table represents in business terms",
      "row_estimate": "small (<10K)|medium (10K-1M)|large (>1M)|unknown",
      "columns": [
        {
          "name": "column name",
          "type": "data type",
          "nullable": true_or_false,
          "is_pk": true_or_false,
          "is_fk": true_or_false,
          "fk_references": "table.column or null",
          "description": "what this column stores in plain English",
          "example_values": ["example1","example2"],
          "constraints": ["NOT NULL","UNIQUE","DEFAULT x"],
          "index": "primary|unique|index|none"
        }
      ],
      "relationships": [
        {"type":"has_many|belongs_to|many_to_many","table":"related_table","via":"junction_table or null"}
      ],
      "common_queries": [
        {
          "description": "what this query does",
          "sql": "actual SQL query"
        }
      ],
      "gotchas": ["common mistakes or surprises with this table"],
      "suggested_indexes": ["CREATE INDEX ... suggestions based on likely queries"]
    }
  ],
  "relationships_overview": "paragraph describing how the main tables relate",
  "mermaid_erd": "complete Mermaid ERD diagram code (erDiagram syntax)",
  "data_dictionary": [
    {"term":"business term","definition":"what it means in this schema","tables":["where it appears"]}
  ],
  "sample_queries": [
    {
      "use_case": "business use case description",
      "sql": "complete runnable SQL query",
      "notes": "performance considerations or caveats"
    }
  ],
  "api_hints": {
    "suggested_endpoints": [
      {"method":"GET|POST|PUT|DELETE","path":"/resource","description":"string","primary_table":"string"}
    ],
    "openapi_partial": "partial OpenAPI 3.0 paths object as JSON string"
  },
  "quality_observations": [
    {
      "type": "missing_index|missing_fk|naming_inconsistency|denormalization|over_normalization|other",
      "severity": "high|medium|low",
      "description": "specific observation",
      "suggestion": "how to fix it"
    }
  ],
  "migration_notes": ["things to be aware of when adding to or modifying this schema"],
  "confidence": 0.0
}"""

def document(schema_source: str, db_name: str = "") -> dict:
    client = anthropic.Anthropic()
    path = Path(schema_source)
    if path.exists():
        text = path.read_text(encoding="utf-8",errors="replace")[:50000]
        db_name = db_name or path.stem.replace("-"," ").replace("_"," ").title()
    else:
        text = schema_source[:50000]

    context = f"Database name: {db_name}\n\n" if db_name else ""
    resp = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=4096, system=SYSTEM,
        messages=[{"role":"user","content":f"Document this database schema:\n\n{context}{text}"}]
    )
    raw = re.sub(r'^```(?:json)?\s*','',resp.content[0].text.strip(),flags=re.MULTILINE)
    raw = re.sub(r'\s*```$','',raw,flags=re.MULTILINE)
    return json.loads(raw)

def to_markdown(r: dict) -> str:
    lines = [
        f"# Database Documentation — {r.get('database_name','')}",
        f"*Dialect: {r.get('dialect','')}*",
        "",
        "## Overview",
        r.get("schema_summary",""),
        "",
        r.get("relationships_overview",""),
        "",
        "---",
        "",
        "## Entity Relationship Diagram",
        "",
        "```mermaid",
        r.get("mermaid_erd","erDiagram\n    %% No ERD generated"),
        "```",
        "",
        "---",
        "",
        "## Tables",
        "",
    ]
    for table in r.get("tables",[]):
        lines += [
            f"### `{table.get('name','')}`",
            "",
            table.get("description",""),
            "",
            f"**Estimated size:** {table.get('row_estimate','')}",
            "",
            "| Column | Type | Nullable | Description |",
            "|--------|------|----------|-------------|",
        ]
        for col in table.get("columns",[]):
            pk = " 🔑" if col.get("is_pk") else ""
            fk = f" → {col.get('fk_references','')}" if col.get("is_fk") else ""
            null = "Yes" if col.get("nullable") else "No"
            lines.append(f"| `{col.get('name','')}`{pk}{fk} | {col.get('type','')} | {null} | {col.get('description','')} |")

        queries = table.get("common_queries",[])
        if queries:
            lines += ["","**Common queries:**",""]
            for q in queries:
                lines += [f"*{q.get('description','')}*","```sql",q.get("sql",""),"```",""]

        gotchas = table.get("gotchas",[])
        if gotchas:
            lines += ["**⚠ Gotchas:**"]
            for g in gotchas: lines.append(f"- {g}")

        indexes = table.get("suggested_indexes",[])
        if indexes:
            lines += ["","**Suggested indexes:**","```sql"] + indexes + ["```"]
        lines.append("")

    sq = r.get("sample_queries",[])
    if sq:
        lines += ["---","","## Sample Queries",""]
        for q in sq:
            lines += [f"### {q.get('use_case','')}", "```sql", q.get("sql",""), "```"]
            if q.get("notes"): lines.append(f"*{q['notes']}*")
            lines.append("")

    dd = r.get("data_dictionary",[])
    if dd:
        lines += ["---","","## Data Dictionary","","| Term | Definition | Tables |","|-|-|-|"]
        for d in dd:
            lines.append(f"| **{d.get('term','')}** | {d.get('definition','')} | {', '.join(d.get('tables',[]))} |")
        lines.append("")

    obs = r.get("quality_observations",[])
    if obs:
        lines += ["---","","## Quality Observations",""]
        sev_icon = {"high":"🔴","medium":"🟡","low":"🔵"}
        for o in obs:
            lines.append(f"{sev_icon.get(o.get('severity','low'),'')} **{o.get('type','').replace('_',' ').title()}**: {o.get('description','')}")
            if o.get("suggestion"): lines.append(f"   → {o['suggestion']}")
        lines.append("")

    return "\n".join(lines)

def print_summary(r: dict):
    tables = r.get("tables",[])
    print(f"\n{'═'*60}")
    print(f"  SCHEMA DOCUMENTER — {r.get('database_name','?')}")
    print(f"  {r.get('dialect','?').upper()} | {len(tables)} tables")
    print(f"{'═'*60}")
    print(f"\n  {r.get('schema_summary','')}")

    print(f"\n  TABLES")
    for t in tables:
        col_count = len(t.get("columns",[]))
        rels = len(t.get("relationships",[]))
        print(f"  {'`'+t.get('name','')+'`':<30} {col_count} cols | {rels} relationships | {t.get('row_estimate','?')}")
        print(f"     {t.get('description','')[:70]}")

    obs = r.get("quality_observations",[])
    high_obs = [o for o in obs if o.get("severity")=="high"]
    if high_obs:
        print(f"\n  SCHEMA ISSUES ({len(high_obs)} high severity)")
        for o in high_obs[:4]: print(f"  🔴 {o.get('description','')}")

    sq = r.get("sample_queries",[])
    if sq:
        print(f"\n  SAMPLE QUERIES ({len(sq)})")
        for q in sq[:3]: print(f"  • {q.get('use_case','')}")

    if r.get("mermaid_erd"):
        print(f"\n  ✅ Mermaid ERD included")
    print(f"\n  Confidence: {int(r.get('confidence',0)*100)}%")
    print(f"{'═'*60}\n")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Auto-generate documentation for any database schema")
    p.add_argument("schema", help="SQL schema file or raw DDL text")
    p.add_argument("--name","-n",default="",help="Database name")
    p.add_argument("--json",action="store_true")
    p.add_argument("--markdown","-m",help="Save as markdown documentation file")
    a = p.parse_args()
    r = document(a.schema, a.name)
    if a.markdown:
        Path(a.markdown).write_text(to_markdown(r),encoding="utf-8")
        print(f"Documentation saved to {a.markdown}")
    if a.json: print(json.dumps(r,indent=2,ensure_ascii=False))
    else: print_summary(r)
