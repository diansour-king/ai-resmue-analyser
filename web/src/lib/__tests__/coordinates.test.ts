import { describe, expect, it } from "vitest";

import { renderScale, toDisplayRect } from "../coordinates";
import type { PageInfo } from "../types";

const a4: PageInfo = {
  page_number: 1,
  width_pt: 595,
  height_pt: 842,
  rotation: 0,
  render_width_px: 1653,
  render_height_px: 2339,
  render_dpi: 200,
  render_available: true,
};

describe("toDisplayRect", () => {
  it("maps a box to the same fraction of the image it occupies on the page", () => {
    const rect = toDisplayRect({ x0: 0, y0: 0, x1: 595, y1: 842 }, a4, {
      width: 1190,
      height: 1684,
    });

    expect(rect).toEqual({ left: 0, top: 0, width: 1190, height: 1684 });
  });

  it("halves with the displayed size, so a resized page stays aligned", () => {
    const box = { x0: 72, y0: 100, x1: 172, y1: 120 };
    const large = toDisplayRect(box, a4, { width: 1190, height: 1684 });
    const small = toDisplayRect(box, a4, { width: 595, height: 842 });

    expect(small.left).toBeCloseTo(large.left / 2);
    expect(small.width).toBeCloseTo(large.width / 2);
  });

  it("places a box at the point offset scaled by the display ratio", () => {
    const rect = toDisplayRect({ x0: 72, y0: 421, x1: 172, y1: 431 }, a4, {
      width: 595,
      height: 842,
    });

    expect(rect.left).toBeCloseTo(72);
    expect(rect.top).toBeCloseTo(421);
    expect(rect.width).toBeCloseTo(100);
  });

  it("never collapses a thin box to nothing", () => {
    const rect = toDisplayRect({ x0: 10, y0: 10, x1: 10, y1: 10 }, a4, {
      width: 100,
      height: 140,
    });

    expect(rect.width).toBeGreaterThan(0);
    expect(rect.height).toBeGreaterThan(0);
  });

  it("does not divide by zero when the page has no geometry yet", () => {
    const empty = { ...a4, width_pt: 0, height_pt: 0 };

    expect(() => toDisplayRect({ x0: 1, y0: 1, x1: 2, y1: 2 }, empty, { width: 10, height: 10 }))
      .not.toThrow();
  });
});

describe("renderScale", () => {
  it("reports the pixels per point the worker used", () => {
    expect(renderScale(a4)).toBeCloseTo(200 / 72, 2);
  });

  it("is unknown until the page has been rendered", () => {
    expect(renderScale({ ...a4, render_width_px: null })).toBeNull();
  });
});
