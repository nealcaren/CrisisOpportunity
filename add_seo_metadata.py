#!/usr/bin/env python3
"""
Script to add SEO metadata to article markdown files.
This adds description, keywords, canonical URLs, and Open Graph/Twitter metadata.
"""

import csv
import os
import re

def read_csv_to_dict(filename):
    """Read CSV file and return list of dictionaries."""
    with open(filename, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

# Read the articles CSV
articles = read_csv_to_dict('articles.csv')

def generate_description(title, author, journal, year):
    """Generate SEO-friendly description for an article."""
    # Remove HTML tags from title
    clean_title = re.sub(r'<[^>]+>', '', title).replace('&nbsp;', ' ')
    return f"{author}'s {year} article '{clean_title}' published in {journal}. Historical sociology examining race relations, urban life, and social dynamics in early 20th century America."

def generate_keywords(author, title, journal):
    """Generate keywords for an article."""
    # Extract author last name
    author_parts = author.replace('.', '').split()
    last_name = author_parts[-1] if author_parts else author

    # Base keywords
    keywords = [last_name, "Black sociology", "historical sociology", "race relations"]

    # Add topic-specific keywords based on title
    title_lower = title.lower()
    if 'migration' in title_lower or 'move' in title_lower:
        keywords.append("Great Migration")
    if 'chicago' in title_lower or 'harlem' in title_lower or 'urban' in title_lower:
        keywords.append("urban sociology")
    if 'labor' in title_lower or 'work' in title_lower or 'economic' in title_lower:
        keywords.append("labor economics")
    if 'crime' in title_lower or 'delinquency' in title_lower:
        keywords.append("criminology")
    if 'women' in title_lower or 'woman' in title_lower:
        keywords.append("gender studies")

    return ", ".join(keywords)

# Process each article
for row in articles:
    article_url = row['article_url']
    md_file = f'markdown/{article_url}.md'

    if not os.path.exists(md_file):
        print(f"Skipping {md_file} - file not found")
        continue

    # Read the markdown file
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if SEO metadata already exists
    if 'description:' in content and 'og-url:' in content and 'article_url:' in content:
        print(f"Skipping {md_file} - SEO metadata already exists")
        continue

    # Split YAML front matter and body
    parts = content.split('---\n', 2)
    if len(parts) >= 3:
        yaml_content = parts[1]
        body = parts[2]

        # Extract info from CSV row
        title = row['title']
        author_name = row['author']
        journal = row['Journal']
        year = row['Year']
        art_slug = row.get('artpng', 'logo1')

        # Generate SEO fields
        description = generate_description(title, author_name, journal, year)
        keywords = generate_keywords(author_name, title, journal)
        canonical_url = f"https://crisisopportunity.org/articles/{article_url}.html"
        og_image = f"https://crisisopportunity.org/Images/{art_slug}.png"

        # Create short title for OG (remove HTML)
        og_title = re.sub(r'<[^>]+>', '', title).replace('&nbsp;', ' ')
        if len(og_title) > 60:
            og_title = og_title[:57] + '...'
        og_title = f"{og_title} - {author_name} ({year})"
        og_desc = f"{author_name}'s historical sociology article from {year}."

        # Add SEO metadata to YAML
        seo_yaml = f"""article_url: "{article_url}"
description: "{description}"
keywords: "{keywords}"
canonical: "{canonical_url}"
og-url: "{canonical_url}"
og-title: "{og_title}"
og-description: "{og_desc}"
og-image: "{og_image}"
twitter-url: "{canonical_url}"
twitter-title: "{og_title}"
twitter-description: "{og_desc}"
twitter-image: "{og_image}"
"""

        # Reconstruct file
        new_content = f"---\n{yaml_content.rstrip()}\n{seo_yaml}---\n{body}"

        # Write back
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"Updated {md_file}")
    else:
        print(f"Skipping {md_file} - no YAML front matter found")

print("\nSEO metadata added to all article markdown files!")
