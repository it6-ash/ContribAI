"use client";

import dynamic from "next/dynamic";

/** `ssr: false` is only legal inside a Client Component, and the landing page
 *  is a Server Component. This wrapper exists solely to own that boundary.
 *
 *  Three.js is a large bundle and WebGL cannot run on the server, so the scene
 *  loads on demand behind a placeholder of the same height: no layout shift
 *  when it arrives, and nobody pays for it above the fold.
 */
const MatchSpace = dynamic(() => import("./MatchSpace"), {
  ssr: false,
  loading: () => (
    <div
      className="panel h-[440px] w-full animate-pulse lg:h-[560px]"
      aria-label="Loading the match space"
    />
  ),
});

export function MatchSpaceLazy() {
  return <MatchSpace />;
}
