import type { BBox, PageInfo } from "./types";

export type DisplayRect = { left: number; top: number; width: number; height: number };

/**
 * Turn a rectangle in PDF points into one in displayed pixels.
 *
 * The scale is derived from the page's own geometry and the size the image is currently
 * being displayed at. Nothing is hardcoded: the render DPI is a server-side decision and the
 * displayed size changes with the window, so a fixed factor would be wrong the moment either
 * changed.
 *
 * The API deliberately gives us both geometries. 200 DPI happens to be 200/72 times the
 * point size today, and this function never needs to know that.
 */
export function toDisplayRect(bbox: BBox, page: PageInfo, displayed: {
  width: number;
  height: number;
}): DisplayRect {
  const scaleX = page.width_pt > 0 ? displayed.width / page.width_pt : 0;
  const scaleY = page.height_pt > 0 ? displayed.height / page.height_pt : 0;
  return {
    left: bbox.x0 * scaleX,
    top: bbox.y0 * scaleY,
    width: Math.max((bbox.x1 - bbox.x0) * scaleX, 1),
    height: Math.max((bbox.y1 - bbox.y0) * scaleY, 1),
  };
}

/**
 * The pixels-per-point the worker rendered at.
 *
 * Only ever shown to a human, so they can see the two coordinate spaces are consistent. The
 * overlay does not use it: it measures the image on screen instead, which stays correct when
 * the page is scaled to fit.
 */
export function renderScale(page: PageInfo): number | null {
  if (!page.render_width_px || page.width_pt <= 0) return null;
  return page.render_width_px / page.width_pt;
}
