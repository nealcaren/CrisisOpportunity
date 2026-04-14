#!/usr/bin/env python3
"""
One-time cleanup: remove duplicate SEO YAML blocks that `add_seo_metadata.py`
produced by running twice. Keeps the FIRST occurrence of each key so pandoc
sees a clean, unambiguous YAML front matter.
"""

import os
import re

SEO_KEYS = {
    "description",
    "keywords",
    "canonical",
    "og-url",
    "og-title",
    "og-description",
    "og-image",
    "twitter-url",
    "twitter-title",
    "twitter-description",
    "twitter-image",
    "article_url",
}


def dedupe_yaml(yaml_text: str) -> tuple[str, int]:
    """Return (cleaned_yaml, removed_line_count)."""
    seen_keys: set[str] = set()
    out_lines: list[str] = []
    removed = 0
    for line in yaml_text.splitlines(keepends=True):
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_\-]*)\s*:", line)
        if m:
            key = m.group(1)
            if key in SEO_KEYS:
                if key in seen_keys:
                    removed += 1
                    continue
                seen_keys.add(key)
        out_lines.append(line)
    return "".join(out_lines), removed


def main() -> None:
    md_dir = "markdown"
    touched = 0
    for fn in sorted(os.listdir(md_dir)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(md_dir, fn)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        parts = content.split("---\n", 2)
        if len(parts) < 3:
            continue
        _, yaml_text, body = parts
        cleaned, removed = dedupe_yaml(yaml_text)
        if removed:
            new_content = f"---\n{cleaned}---\n{body}"
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"{fn}: removed {removed} duplicate SEO lines")
            touched += 1
    print(f"\nDone. {touched} files cleaned.")


if __name__ == "__main__":
    main()
