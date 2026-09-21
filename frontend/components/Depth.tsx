"use client";

import { useEffect } from "react";

/** One depth layer for the whole site.
 *
 *  Installed once in the root layout rather than wired into each component.
 *  Two behaviours, both driven by CSS custom properties written from a single
 *  listener, so no React state changes and nothing re-renders on pointer move:
 *
 *    [data-tilt]  a surface that leans toward the pointer
 *    [data-depth] a block that rises out of the page as it scrolls in
 *
 *  Everything animates transform and opacity only, and the whole layer is
 *  inert under prefers-reduced-motion: a page that pitches and rotates is
 *  exactly what that setting exists to switch off.
 */
export function Depth() {
  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;

    document.documentElement.dataset.depth3d = "on";

    // ---- tilt ---------------------------------------------------------
    // One delegated listener, rAF-throttled. Per-card React state here would
    // re-render the tree on every mouse move and collapse on a trackpad.
    let frame = 0;
    let pending: { el: HTMLElement; x: number; y: number } | null = null;

    const apply = () => {
      frame = 0;
      if (!pending) return;
      const { el, x, y } = pending;
      el.style.setProperty("--tx", x.toFixed(3));
      el.style.setProperty("--ty", y.toFixed(3));
    };

    const onMove = (e: PointerEvent) => {
      const el = (e.target as HTMLElement | null)?.closest<HTMLElement>("[data-tilt]");
      if (!el) return;
      const r = el.getBoundingClientRect();
      // -0.5..0.5 from the centre, so the lean follows the cursor.
      pending = {
        el,
        x: (e.clientX - r.left) / r.width - 0.5,
        y: (e.clientY - r.top) / r.height - 0.5,
      };
      if (!frame) frame = requestAnimationFrame(apply);
    };

    const onLeave = (e: PointerEvent) => {
      const el = (e.target as HTMLElement | null)?.closest<HTMLElement>("[data-tilt]");
      if (!el) return;
      el.style.setProperty("--tx", "0");
      el.style.setProperty("--ty", "0");
    };

    document.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerout", onLeave, { passive: true });

    // ---- depth entrance ------------------------------------------------
    // IntersectionObserver, not a scroll handler: a scroll handler runs on
    // every frame of every scroll anywhere on the page.
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          entry.target.classList.remove("depth-armed");
          entry.target.classList.add("depth-in");
          io.unobserve(entry.target); // one-way; re-animating on scroll-up is nausea
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.02 },
    );

    // Arm only what is genuinely below the fold. Anything already on screen is
    // left alone and stays visible, so a block can never be hidden waiting for
    // an observer callback that may not come.
    const arm = () => {
      const fold = window.innerHeight;
      document
        .querySelectorAll<HTMLElement>("[data-depth]:not(.depth-in):not(.depth-armed)")
        .forEach((el) => {
          if (el.getBoundingClientRect().top > fold * 0.9) el.classList.add("depth-armed");
          io.observe(el);
        });
    };
    arm();

    // Last resort. If anything is still armed well after load, something went
    // wrong and a visible page beats a faithful animation.
    const failsafe = window.setTimeout(() => {
      document.querySelectorAll(".depth-armed").forEach((el) => {
        el.classList.remove("depth-armed");
        el.classList.add("depth-in");
      });
    }, 4000);

    // Client-routed pages mount new nodes after this effect has run.
    const mo = new MutationObserver(arm);
    mo.observe(document.body, { childList: true, subtree: true });

    return () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerout", onLeave);
      io.disconnect();
      mo.disconnect();
      clearTimeout(failsafe);
      cancelAnimationFrame(frame);
      delete document.documentElement.dataset.depth3d;
    };
  }, []);

  return null;
}
