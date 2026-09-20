"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

/** The scoring model, as space.
 *
 *  Three of the eight dimensions become axes, so "close to you" literally means
 *  "a good fit". That is the one thing in this product genuinely worth showing
 *  in three dimensions: a bar chart can rank issues, but it cannot show that
 *  two issues are near each other and far from a third.
 *
 *  Deliberately not on the dashboard. That screen is for triage, where reading
 *  speed beats everything, and a canvas there would be decoration.
 */
const AXES: Array<[key: string, label: string]> = [
  ["skill_match", "Skill match"],
  ["difficulty_match", "Difficulty fit"],
  ["issue_clarity", "Issue clarity"],
];

export interface SpacePoint {
  id: number;
  title: string;
  repo: string;
  fit: number;
  x: number;
  y: number;
  z: number;
}

/** Sample data for the landing page: the real shape the engine produces, not
 *  invented numbers dressed up as a product. */
const SAMPLE: SpacePoint[] = [
  { id: 1, title: "Pagination returns wrong page offsets", repo: "ledgerly/ledgerly-api", fit: 0.91, x: 0.92, y: 1.0, z: 0.95 },
  { id: 2, title: "CSV import silently drops rows", repo: "ledgerly/ledgerly-api", fit: 0.88, x: 0.9, y: 1.0, z: 0.8 },
  { id: 3, title: "Add currency code validation", repo: "ledgerly/ledgerly-api", fit: 0.85, x: 0.88, y: 0.75, z: 0.9 },
  { id: 4, title: "Retry backoff ignores jitter", repo: "pipeforge/pipeforge", fit: 0.82, x: 0.7, y: 1.0, z: 0.85 },
  { id: 5, title: "Generated signatures lose defaults", repo: "docsmith/docsmith", fit: 0.78, x: 0.68, y: 0.75, z: 0.72 },
  { id: 6, title: "LRU eviction ignores per-key TTL", repo: "orbitcache/orbit", fit: 0.44, x: 0.2, y: 0.45, z: 0.7 },
  { id: 7, title: "Dialog does not return focus", repo: "vela-ui/vela", fit: 0.38, x: 0.15, y: 0.7, z: 0.9 },
  { id: 8, title: "Rewrite theming on cascade layers", repo: "vela-ui/vela", fit: 0.21, x: 0.12, y: 0.1, z: 0.4 },
  { id: 9, title: "Rebalance drops keys on rejoin", repo: "orbitcache/orbit", fit: 0.18, x: 0.1, y: 0.1, z: 0.3 },
];

const SPAN = 3.4;

/** Read the live theme tokens. A scene that hardcodes its own colours either
 *  washes out on a light page or inverts it, and inverting one section is the
 *  thing the page theme lock exists to prevent. */
function readTheme() {
  if (typeof window === "undefined") {
    return { accent: "#5b9cff", ink: "#e6e8ee", axis: "#2a3040" };
  }
  const css = getComputedStyle(document.documentElement);
  const pick = (name: string, fallback: string) =>
    css.getPropertyValue(name).trim() || fallback;
  return {
    accent: pick("--accent", "#5b9cff"),
    ink: pick("--foreground", "#e6e8ee"),
    axis: pick("--border", "#2a3040"),
  };
}
const toWorld = (p: SpacePoint) =>
  new THREE.Vector3((p.x - 0.5) * SPAN, (p.y - 0.5) * SPAN, (p.z - 0.5) * SPAN);

function Issue({
  point,
  onHover,
  accent,
}: {
  point: SpacePoint;
  onHover: (p: SpacePoint | null) => void;
  accent: THREE.Color;
}) {
  const pos = useMemo(() => toWorld(point), [point]);
  const [over, setOver] = useState(false);
  // Fit is encoded twice, by size and by lightness, because either alone is
  // hard to judge in perspective. Not by opacity: a translucent sphere simply
  // disappears against a light page.
  const size = 0.08 + point.fit * 0.11;
  const colour = useMemo(
    () => accent.clone().lerp(new THREE.Color("#8d93a4"), 1 - point.fit),
    [accent, point.fit],
  );

  return (
    <mesh
      position={pos}
      onPointerOver={(e: { stopPropagation: () => void }) => {
        e.stopPropagation();
        setOver(true);
        onHover(point);
      }}
      onPointerOut={() => {
        setOver(false);
        onHover(null);
      }}
    >
      <sphereGeometry args={[size, 24, 24]} />
      <meshStandardMaterial
        color={colour}
        emissive={colour}
        emissiveIntensity={over ? 0.9 : 0.1 + point.fit * 0.35}
        roughness={0.35}
        metalness={0.05}
      />
    </mesh>
  );
}

function Scene({
  onHover,
  animate,
  progress,
}: {
  onHover: (p: SpacePoint | null) => void;
  animate: boolean;
  progress: React.RefObject<number>;
}) {
  const group = useRef<THREE.Group>(null);
  const theme = useMemo(readTheme, []);
  const accent = useMemo(() => new THREE.Color(theme.accent), [theme.accent]);
  const best = SAMPLE[0];
  const { camera } = useThree();

  useFrame((_, delta) => {
    const t = progress.current ?? 0;

    // Scroll drives the orbit. Reading position beats a timer: the reader sets
    // the pace, and scrubbing back rewinds the explanation rather than
    // replaying it out of order.
    if (group.current) {
      const target = t * Math.PI * 1.15;
      group.current.rotation.y +=
        (target - group.current.rotation.y) * Math.min(1, delta * 4);
      if (animate && t <= 0.001) group.current.rotation.y += delta * 0.12;
    }

    // Pull in as the section is read, so a cloud resolves into a structure.
    const radius = 5.6 - t * 1.9;
    const height = 2.4 - t * 0.8;
    camera.position.lerp(
      new THREE.Vector3(radius * 0.72, height, radius * 0.72),
      Math.min(1, delta * 3),
    );
    camera.lookAt(0, 0, 0);
  });

  return (
    <group ref={group}>
      <ambientLight intensity={1.6} />
      <directionalLight position={[4, 6, 5]} intensity={2.2} />
      <directionalLight position={[-5, -2, -4]} intensity={0.7} />

      {/* You, at the origin. Distance from here is the whole metaphor. */}
      <mesh>
        <sphereGeometry args={[0.17, 28, 28]} />
        <meshStandardMaterial
          color={theme.ink}
          emissive={theme.ink}
          emissiveIntensity={0.25}
          roughness={0.3}
        />
      </mesh>

      {AXES.map((_, i) => (
        <Axis key={i} index={i} progress={progress} colour={theme.accent} />
      ))}

      {/* One line, to the best match. Lines to everything would be a hairball. */}
      <primitive
        object={
          new THREE.Line(
            new THREE.BufferGeometry().setFromPoints([
              new THREE.Vector3(0, 0, 0),
              toWorld(best),
            ]),
            new THREE.LineBasicMaterial({
              color: theme.accent,
              transparent: true,
              opacity: 0.75,
            }),
          )
        }
      />

      {SAMPLE.map((p) => (
        <Issue key={p.id} point={p} onHover={onHover} accent={accent} />
      ))}
    </group>
  );
}

/** One axis, brightening when the scroll reaches its third of the section. */
function Axis({
  index,
  progress,
  colour,
}: {
  index: number;
  progress: React.RefObject<number>;
  colour: string;
}) {
  const mat = useRef<THREE.LineBasicMaterial | null>(null);
  const line = useMemo(() => {
    const dir = [
      new THREE.Vector3(SPAN / 2, 0, 0),
      new THREE.Vector3(0, SPAN / 2, 0),
      new THREE.Vector3(0, 0, SPAN / 2),
    ][index];
    const geometry = new THREE.BufferGeometry().setFromPoints([
      dir.clone().negate(),
      dir,
    ]);
    const material = new THREE.LineBasicMaterial({
      color: colour,
      transparent: true,
      opacity: 0.12,
    });
    mat.current = material;
    return new THREE.Line(geometry, material);
  }, [index, colour]);

  // Introduced one at a time. All three at once is an unreadable cage.
  useFrame(() => {
    const t = progress.current ?? 0;
    const lit = Math.max(0, Math.min(1, t * 3 - index));
    if (mat.current) mat.current.opacity = 0.12 + lit * 0.62;
  });

  return <primitive object={line} />;
}

export default function MatchSpace() {
  const [hovered, setHovered] = useState<SpacePoint | null>(null);
  const [axisLit, setAxisLit] = useState(0);
  const host = useRef<HTMLDivElement>(null);
  const progress = useRef(0);
  const reduced =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const shown = hovered ?? SAMPLE[0];

  // Scroll position via IntersectionObserver plus rAF, not a scroll listener.
  // A listener fires on every frame of every scroll on the page, including
  // while this section is nowhere near the viewport.
  useEffect(() => {
    if (reduced || !host.current) return;
    const el = host.current;
    let raf = 0;
    let visible = false;

    const measure = () => {
      const rect = el.getBoundingClientRect();
      const span = window.innerHeight + rect.height;
      const seen = window.innerHeight - rect.top;
      const t = Math.max(0, Math.min(1, seen / span));
      progress.current = t;
      setAxisLit(Math.min(AXES.length, Math.floor(t * 3) + 1));
      if (visible) raf = requestAnimationFrame(measure);
    };

    const io = new IntersectionObserver(
      ([entry]) => {
        visible = entry.isIntersecting;
        cancelAnimationFrame(raf);
        if (visible) raf = requestAnimationFrame(measure);
      },
      { threshold: 0 },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [reduced]);

  return (
    <div ref={host} className="panel relative overflow-hidden">
      <div className="h-[440px] w-full lg:h-[560px]">
        <Canvas
          camera={{ position: [3.6, 2.4, 3.6], fov: 42 }}
          dpr={[1, 1.75]}
          // Render only when something changes while motion is reduced; a
          // permanently spinning canvas on a laptop battery is rude.
          frameloop={reduced ? "demand" : "always"}
          gl={{ antialias: true, powerPreference: "high-performance" }}
        >
          <Scene onHover={setHovered} animate={!reduced} progress={progress} />
        </Canvas>
      </div>

      <div className="pointer-events-none absolute left-5 top-5 max-w-[60%]">
        <p className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-muted">
          {hovered ? "hovering" : "closest match"}
        </p>
        <p className="mt-1.5 text-[14px] font-medium leading-snug">{shown.title}</p>
        <p className="font-mono text-[11.5px] text-muted">
          {shown.repo} · {Math.round(shown.fit * 100)}% fit
        </p>
      </div>

      <div className="pointer-events-none absolute bottom-4 left-5 right-5 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[10.5px] text-muted">
        {AXES.map(([, label], i) => (
          <span
            key={label}
            className={i < axisLit || reduced ? "text-accent" : undefined}
          >
            {["x", "y", "z"][i]} · {label}
          </span>
        ))}
        <span className="ml-auto">near the centre means a better fit</span>
      </div>
    </div>
  );
}
