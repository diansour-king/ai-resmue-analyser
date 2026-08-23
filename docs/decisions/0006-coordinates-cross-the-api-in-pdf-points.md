# 0006. Coordinates cross the API in PDF points, and the viewer computes its own scale

Status: accepted
Date: 2026-08-23

## Context

A finding has to be drawn over a rendered page. The integrity engine produces rectangles in PDF
user space; the browser draws in CSS pixels; the render sits at 200 DPI in between. Something
has to convert, and where that conversion lives decides what breaks when any of the three
change.

## Options considered

**Store pixel coordinates at render time.** The viewer would place rectangles directly. Rejected:
it bakes the render DPI into the database. Changing the DPI would mean rewriting every stored
finding, and a finding would stop meaning anything about the document itself.

**Send a scale factor with the findings.** Rejected: correct only while the image is displayed at
its natural size. The page is scaled to fit its pane and rescaled on every window resize, so a
factor computed on the server is wrong as soon as it arrives.

**Send points and page geometry; let the viewer measure.** Chosen.

## Decision

The database stores `x0, y0, x1, y1` as double precision in **PDF points, 72 to the inch, origin
top-left**. This is exactly what the integrity engine emitted, unmodified.

The API serves those same points, and serves each page's geometry alongside: `width_pt`,
`height_pt`, `render_width_px`, `render_height_px`, `render_dpi`.

The viewer measures the image as displayed and derives its own scale:

```
scaleX = displayedWidthPx / page.width_pt
left   = bbox.x0 * scaleX
```

That is the whole transform. It lives in one function, `web/src/lib/coordinates.ts`, it is unit
tested, and no factor is hardcoded anywhere in the frontend. A `ResizeObserver` on the image
recomputes it, so the overlay follows the page through any resize.

`render_width_px / width_pt` is `render_dpi / 72` by construction. A worker test asserts that
directly, because if the two ever disagree the overlay drifts silently and nothing about a
screenshot would reveal it.

## Consequences

- Changing the render DPI requires no data migration and no frontend change.
- Serving a page at a different size, a thumbnail or a print view, needs no new coordinate data.
- The frontend owns one conversion function and is the only place that knows about pixels.
- Rotated pages are stored but not yet applied. `rotation` travels through the API and the
  viewer ignores it, so a page with a non-zero rotation would place overlays wrongly. No fixture
  exercises this yet; it is recorded in the phase 2 limitations.
