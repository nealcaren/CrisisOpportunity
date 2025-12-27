#!/bin/bash
# Script to optimize images for Crisis & Opportunity website

echo "=== Image Optimization Script ==="
echo "This script will:"
echo "  1. Compress PNG images using pngquant"
echo "  2. Create WebP versions for modern browsers"
echo "  3. Keep original files as backups"
echo ""

# Create backup directory
mkdir -p docs/images_backup

# Counter for statistics
total_original=0
total_optimized=0
files_processed=0

# Function to optimize a single PNG file
optimize_png() {
    local file="$1"
    local filename=$(basename "$file")
    local dir=$(dirname "$file")

    # Get original size
    local original_size=$(stat -f%z "$file")

    # Backup original
    cp "$file" "docs/images_backup/$filename"

    # Optimize with pngquant (high quality, 256 colors)
    pngquant --quality=70-95 --force --ext .png "$file" 2>/dev/null

    if [ $? -eq 0 ]; then
        local new_size=$(stat -f%z "$file")
        local savings=$((original_size - new_size))
        local percent=$((savings * 100 / original_size))

        total_original=$((total_original + original_size))
        total_optimized=$((total_optimized + new_size))
        files_processed=$((files_processed + 1))

        echo "  ✓ $filename: $(numfmt --to=iec $original_size) → $(numfmt --to=iec $new_size) (saved ${percent}%)"
    else
        echo "  ⚠ $filename: pngquant failed, skipping"
    fi
}

# Function to create WebP version
create_webp() {
    local file="$1"
    local webp_file="${file%.*}.webp"

    # Only create if doesn't exist or source is newer
    if [ ! -f "$webp_file" ] || [ "$file" -nt "$webp_file" ]; then
        cwebp -q 85 "$file" -o "$webp_file" 2>/dev/null
        if [ $? -eq 0 ]; then
            local webp_size=$(stat -f%z "$webp_file")
            echo "    → Created WebP: $(numfmt --to=iec $webp_size)"
        fi
    fi
}

echo "Optimizing PNG images..."
echo ""

# Optimize the largest article images first
echo "Processing docs/articles/Images/*.png..."
for file in docs/articles/Images/*.png; do
    if [ -f "$file" ]; then
        optimize_png "$file"
        create_webp "$file"
    fi
done

echo ""
echo "Processing docs/Images/*.png..."
# Optimize main Images directory
for file in docs/Images/*.png; do
    if [ -f "$file" ]; then
        # Skip very small images (likely icons)
        size=$(stat -f%z "$file")
        if [ $size -gt 50000 ]; then  # Only optimize files > 50KB
            optimize_png "$file"
            create_webp "$file"
        fi
    fi
done

echo ""
echo "=== Optimization Complete ==="
echo "Files processed: $files_processed"
if [ $files_processed -gt 0 ]; then
    echo "Original total: $(numfmt --to=iec $total_original)"
    echo "Optimized total: $(numfmt --to=iec $total_optimized)"
    savings=$((total_original - total_optimized))
    percent=$((savings * 100 / total_original))
    echo "Total saved: $(numfmt --to=iec $savings) (${percent}%)"
fi
echo ""
echo "Backups stored in: docs/images_backup/"
