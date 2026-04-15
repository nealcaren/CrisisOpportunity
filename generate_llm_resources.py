#!/usr/bin/env python3
"""
Generate LLM-friendly resources for crisisopportunity.org:

  1. Copy markdown/{slug}.md -> docs/articles/{slug}.md so LLMs can fetch
     clean markdown instead of parsing HTML.
  2. Generate docs/llms.txt (https://llmstxt.org format) listing every
     article with author / year / journal, grouped by category.
  3. Inject a Schema.org ScholarlyArticle JSON-LD block into every
     docs/articles/{slug}.html that doesn't already have one. The same
     block is in templates/article_html.template for future rebuilds;
     this handles the already-built HTML without needing a pandoc run.

Run from the repo root:  python generate_llm_resources.py
"""

import csv
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
MD_SRC = ROOT / "markdown"
DOCS = ROOT / "docs"
ARTICLES_DIR = DOCS / "articles"
CSV_PATH = ROOT / "articles.csv"

CATEGORY_ORDER = [
    "Racial Identity",
    "White Racism and Racial Violence",
    "Great Migration and Urban Sociology",
    "Labor and Economics",
    "Gender",
    "Health and Populations",
    "Social Movements",
    "Methods",
    "Crime",
    "Education",
    "Family",
    "Religion",
]


def load_articles():
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    return s.replace("&nbsp;", " ").strip()


def extract_summary(slug: str) -> str | None:
    """Pull summary text from a markdown file's YAML frontmatter.

    Prefers the hand-written `abstract:` field (present on originals where
    the source article carried an abstract) and falls back to the
    editorially-written `editorial_summary:` field produced for this site.
    The distinction matters for rendering: the pandoc template only displays
    `abstract`, so synthetic summaries stay out of the reader-facing HTML
    but still flow into llms.txt and the raw .md files LLMs consume.

    Handles folded/literal block scalars (`>-`, `|`, etc.) and single-line
    quoted forms. Returns whitespace-collapsed text or None.
    """
    path = MD_SRC / f"{slug}.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    if not m:
        return None
    yaml_block = m.group(1)

    for field in ("abstract", "editorial_summary"):
        block = re.search(
            rf"^{field}:\s*[>|][-+]?\s*\n((?:[ \t]+.*\n?)+)",
            yaml_block,
            re.M,
        )
        if block:
            lines = [ln.strip() for ln in block.group(1).splitlines()]
            return " ".join(ln for ln in lines if ln)
        single = re.search(rf"^{field}:[ \t]*(.+)$", yaml_block, re.M)
        if single:
            value = single.group(1).strip()
            if value and value[0] in "\"'" and value[-1] == value[0]:
                value = value[1:-1]
            return value
    return None


# ---------------------------------------------------------------------------
# 1. Copy raw markdown into docs/articles/
# ---------------------------------------------------------------------------
def copy_markdown(articles):
    copied = 0
    for row in articles:
        slug = row["article_url"]
        src = MD_SRC / f"{slug}.md"
        dst = ARTICLES_DIR / f"{slug}.md"
        if not src.exists():
            print(f"  skip (no source): {slug}.md")
            continue
        shutil.copyfile(src, dst)
        copied += 1
    print(f"Copied {copied} markdown files to docs/articles/")


# ---------------------------------------------------------------------------
# 2. Generate docs/llms.txt
# ---------------------------------------------------------------------------
def build_llms_txt(articles):
    lines = []
    lines.append("# Crisis & Opportunity")
    lines.append("")
    lines.append(
        "> A digital repository of early-20th-century sociology works by Black "
        "scholars (1892-1940). Sixty-one articles totaling roughly 261,000 words, "
        "hand-curated from journals such as *The American Journal of Sociology*, "
        "*Opportunity*, *Social Forces*, *The Annals*, and *The Southern Workman*. "
        "All texts are in the public domain. Each article is available as HTML, "
        "plain markdown, and (where available) a PDF scan of the original."
    )
    lines.append("")
    lines.append(
        "Authors include W.E.B. Du Bois, Ida B. Wells, Anna J. Cooper, Kelly Miller, "
        "Monroe N. Work, Charles S. Johnson, E. Franklin Frazier, Abram L. Harris, "
        "Ira De A. Reid, Elizabeth Ross Haynes, Elise Johnson McDougald, Fannie "
        "Barrier Williams, Horace Mann Bond, Ralph J. Bunche, and others."
    )
    lines.append("")
    lines.append("## Site")
    lines.append("")
    lines.append("- [About](https://crisisopportunity.org/about.html): project background and scope")
    lines.append("- [Full article index](https://crisisopportunity.org/index.html): human-readable index of all articles")
    lines.append("- [Artwork credits](https://crisisopportunity.org/art.html): Harlem Renaissance artwork used throughout the site")
    lines.append("- [Sitemap](https://crisisopportunity.org/sitemap.xml): machine-readable sitemap index")
    lines.append("")

    by_cat = {}
    for row in articles:
        by_cat.setdefault(row["Category"], []).append(row)

    ordered_cats = [c for c in CATEGORY_ORDER if c in by_cat]
    for cat in by_cat:
        if cat not in ordered_cats:
            ordered_cats.append(cat)

    for cat in ordered_cats:
        lines.append(f"## {cat}")
        lines.append("")
        rows = sorted(by_cat[cat], key=lambda r: int(r["Year"]))
        for row in rows:
            title = strip_html(row["title"])
            author = row["author"]
            year = row["Year"]
            journal = row["Journal"]
            slug = row["article_url"]
            md_url = f"https://crisisopportunity.org/articles/{slug}.md"
            lines.append(
                f"- [{title}]({md_url}): {author} ({year}), *{journal}*."
            )
            summary = extract_summary(slug)
            if summary:
                lines.append(f"  {summary}")
        lines.append("")

    lines.append("## Optional")
    lines.append("")
    lines.append(
        "- [PDF scans](https://crisisopportunity.org/articles/PDFS/): original "
        "page images for each article where available"
    )
    lines.append("")

    (DOCS / "llms.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote docs/llms.txt ({len(articles)} articles)")


# ---------------------------------------------------------------------------
# 3. Inject JSON-LD into built HTML files
# ---------------------------------------------------------------------------
JSONLD_RE = re.compile(
    r"\s*<!-- Schema\.org JSON-LD -->\s*"
    r'<script type="application/ld\+json">.*?</script>\s*',
    re.S,
)
SUMMARY_DIV_RE = re.compile(
    r'\s*<div class="editorial-summary"[^>]*>.*?</div>\s*',
    re.S,
)


def build_jsonld(row):
    slug = row["article_url"]
    title = strip_html(row["title"])
    authors = [
        {"@type": "Person", "name": a.strip()}
        for a in re.split(r"\s+and\s+|,\s*(?=[A-Z])", row["author"])
        if a.strip()
    ]
    # Fallback: one author if splitting produced nothing useful
    if not authors:
        authors = [{"@type": "Person", "name": row["author"]}]

    md_path = MD_SRC / f"{slug}.md"
    pdf_url = None
    if md_path.exists():
        m = re.search(r"^pdf_URL:\s*(.+)$", md_path.read_text(encoding="utf-8"), re.M)
        if m:
            pdf_url = m.group(1).strip().strip('"').strip("'")

    encodings = [
        {
            "@type": "MediaObject",
            "encodingFormat": "text/html",
            "contentUrl": f"https://crisisopportunity.org/articles/{slug}.html",
        },
        {
            "@type": "MediaObject",
            "encodingFormat": "text/markdown",
            "contentUrl": f"https://crisisopportunity.org/articles/{slug}.md",
        },
    ]
    if pdf_url:
        encodings.append(
            {
                "@type": "MediaObject",
                "encodingFormat": "application/pdf",
                "contentUrl": f"https://crisisopportunity.org/articles/{pdf_url}",
            }
        )

    data = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "headline": title,
        "author": authors,
        "datePublished": row["Year"],
        "isPartOf": {"@type": "Periodical", "name": row["Journal"]},
        "publisher": {
            "@type": "Organization",
            "name": "Crisis & Opportunity",
            "url": "https://crisisopportunity.org",
        },
        "url": f"https://crisisopportunity.org/articles/{slug}.html",
        "inLanguage": "en",
        "isAccessibleForFree": True,
        "license": "https://creativecommons.org/publicdomain/mark/1.0/",
        "encoding": encodings,
    }
    summary = extract_summary(slug)
    if summary:
        data["abstract"] = summary
    return (
        "  <!-- Schema.org JSON-LD -->\n"
        '  <script type="application/ld+json">\n'
        + json.dumps(data, indent=2, ensure_ascii=False)
        + "\n  </script>\n"
    )


def inject_html_extras(articles):
    """Refresh JSON-LD and the hidden editorial-summary div in every built HTML file.

    Idempotent: any existing JSON-LD or editorial-summary div is stripped
    first, then the current version is written. The summary div is only
    rendered when a summary exists and the article did NOT ship with an
    original `abstract:` (those originals display visibly via pandoc).
    """
    jsonld_count = 0
    summary_count = 0
    for row in articles:
        slug = row["article_url"]
        html_path = ARTICLES_DIR / f"{slug}.html"
        if not html_path.exists():
            print(f"  skip (no html): {slug}.html")
            continue
        html = html_path.read_text(encoding="utf-8")

        # 1. Strip old injected blocks so the run is idempotent.
        html = JSONLD_RE.sub("\n", html)
        html = SUMMARY_DIV_RE.sub("\n", html)

        # 2. JSON-LD before </head>
        if "</head>" not in html:
            print(f"  skip (no </head>): {slug}.html")
            continue
        html = html.replace("</head>", build_jsonld(row) + "</head>", 1)
        jsonld_count += 1

        # 3. Hidden editorial-summary div before </body>, only for slugs
        #    whose summary came from `editorial_summary:` (not `abstract:`).
        md_path = MD_SRC / f"{slug}.md"
        summary = extract_summary(slug)
        has_original_abstract = False
        if md_path.exists():
            txt = md_path.read_text(encoding="utf-8")
            m = re.match(r"---\n(.*?)\n---", txt, re.S)
            if m and re.search(r"^abstract:", m.group(1), re.M):
                has_original_abstract = True
        if summary and not has_original_abstract and "</body>" in html:
            # Inline style is belt-and-suspenders — the .editorial-summary
            # class in article_style.css does the same thing, but inline
            # removes any risk of cached CSS rendering the text visibly.
            hide_style = (
                "position:absolute;width:1px;height:1px;padding:0;"
                "margin:-1px;overflow:hidden;clip:rect(0,0,0,0);"
                "white-space:normal;border:0"
            )
            div = (
                f'\n<div class="editorial-summary" role="doc-abstract" '
                f'aria-label="Editorial summary" style="{hide_style}">'
                f"{summary}</div>\n"
            )
            html = html.replace("</body>", div + "</body>", 1)
            summary_count += 1

        html_path.write_text(html, encoding="utf-8")
    print(
        f"Refreshed JSON-LD in {jsonld_count} files; "
        f"injected editorial-summary div in {summary_count} files"
    )


if __name__ == "__main__":
    articles = load_articles()
    copy_markdown(articles)
    build_llms_txt(articles)
    inject_html_extras(articles)
    print("Done.")
