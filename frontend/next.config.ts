import type { NextConfig } from "next";

// Everything the browser calls is same-origin: /api/* is proxied to the backend
// rather than fetched cross-site.
//
// This is not a convenience. With the API on a different host, the session cookie
// is cross-site, so `SameSite=Lax` means the browser never sends it and every
// authenticated request 401s. The alternatives are `SameSite=None; Secure` (which
// opens CSRF on every POST, needing tokens) or this. This is fewer moving parts
// and closes the CSRF surface instead of opening it.
//
// It also keeps the GitHub OAuth callback first-party: GitHub redirects to
// <public-origin>/api/auth/github/callback, the proxy forwards it, and the cookie
// the backend sets lands on the origin the user is actually browsing.
const apiTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Self-contained server bundle, so the runtime image does not need node_modules.
  output: "standalone",

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiTarget}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
