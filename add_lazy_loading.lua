-- Pandoc Lua filter to add loading="lazy" to all images
-- This improves page performance by deferring image loading until they're near the viewport

function Image(img)
  -- Add loading="lazy" attribute to all images
  img.attributes['loading'] = 'lazy'
  return img
end
