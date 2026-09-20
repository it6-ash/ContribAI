"use client";

import { useRef, type ReactNode } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(ScrollTrigger, useGSAP);

/** True when the visitor asked the OS to reduce motion. Every animation in
 *  this file degrades to its finished state rather than a faster version. */
export const reduced = () =>
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Reveal children in document order as the block enters the viewport.
 *  Batched, so twelve cards produce one staggered animation, not twelve
 *  competing ones. */
export function Reveal({
  children,
  className = "",
  y = 22,
  stagger = 0.07,
  selector = ":scope > *",
}: {
  children: ReactNode;
  className?: string;
  y?: number;
  stagger?: number;
  selector?: string;
}) {
  const root = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const items = gsap.utils.toArray<HTMLElement>(
        root.current!.querySelectorAll(selector),
      );
      if (!items.length) return;
      if (reduced()) {
        gsap.set(items, { opacity: 1, y: 0 });
        return;
      }
      gsap.from(items, {
        opacity: 0,
        y,
        duration: 0.7,
        stagger,
        ease: "power3.out",
        scrollTrigger: { trigger: root.current, start: "top 82%", once: true },
      });
    },
    { scope: root },
  );

  return (
    <div ref={root} className={className}>
      {children}
    </div>
  );
}

/** Count a number up when it scrolls into view. Used for the figures that are
 *  the point of a section, never for decoration. */
export function CountUp({
  to,
  suffix = "",
  duration = 1.1,
  className = "",
}: {
  to: number;
  suffix?: string;
  duration?: number;
  className?: string;
}) {
  const el = useRef<HTMLSpanElement>(null);

  useGSAP(
    () => {
      const node = el.current!;
      if (reduced()) {
        node.textContent = `${to}${suffix}`;
        return;
      }
      const obj = { v: 0 };
      gsap.to(obj, {
        v: to,
        duration,
        ease: "power2.out",
        scrollTrigger: { trigger: node, start: "top 90%", once: true },
        onUpdate: () => {
          node.textContent = `${Math.round(obj.v)}${suffix}`;
        },
      });
    },
    { scope: el },
  );

  return (
    <span ref={el} className={`tnum ${className}`}>
      0{suffix}
    </span>
  );
}

/** Headline that assembles itself word by word. One per page: it is a
 *  hierarchy device for the single most important sentence, and it stops
 *  meaning anything if every heading does it. */
export function WordReveal({
  text,
  className = "",
}: {
  text: string;
  className?: string;
}) {
  const root = useRef<HTMLHeadingElement>(null);

  useGSAP(
    () => {
      const words = gsap.utils.toArray<HTMLElement>(
        root.current!.querySelectorAll("[data-w]"),
      );
      if (reduced()) {
        gsap.set(words, { opacity: 1, y: 0 });
        return;
      }
      gsap.from(words, {
        opacity: 0,
        y: "0.5em",
        duration: 0.85,
        stagger: 0.045,
        ease: "power3.out",
        delay: 0.1,
      });
    },
    { scope: root },
  );

  return (
    <h1 ref={root} className={className}>
      {text.split(" ").map((w, i) => (
        // The clipping span is what makes the word rise out of a mask rather
        // than just fade. Descenders need the padding or they get sheared.
        <span key={i} className="inline-block overflow-hidden pb-[0.08em] align-bottom">
          <span data-w className="inline-block">
            {w}
            {i < text.split(" ").length - 1 ? " " : ""}
          </span>
        </span>
      ))}
    </h1>
  );
}
