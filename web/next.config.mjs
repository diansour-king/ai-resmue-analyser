/** @type {import('next').NextConfig} */

// Where the /v1 proxy sends requests, in order of preference:
//   1. API_ORIGIN, set explicitly by whoever deployed this.
//   2. On Render (which sets RENDER=true in every service), the API service's public URL.
//      This is a safety net, not the intended path: a Render *code* deploy does not re-read
//      render.yaml's env vars — only a blueprint sync does — so a service can end up running
//      new code with no API_ORIGIN and silently proxy to a hostname that does not resolve.
//      Change this if the API service is ever renamed.
//   3. The docker-compose service name, for `make dev` locally.
const DEV_COMPOSE_ORIGIN = "http://api:8000";
const RENDER_API_ORIGIN = "https://careerlayer-api.onrender.com";

const apiOrigin =
  process.env.API_ORIGIN ?? (process.env.RENDER ? RENDER_API_ORIGIN : DEV_COMPOSE_ORIGIN);

// Printed once at boot. When the proxy 500s, the first question is always "which origin did
// it resolve to", and this puts the answer in the deploy log instead of in a guess.
console.log(
  `[careerlayer-web] proxying /v1/* to ${apiOrigin}` +
    (process.env.API_ORIGIN ? " (from API_ORIGIN)" : " (fallback — API_ORIGIN is not set)"),
);

const config = {
  // The browser only ever talks to this origin. Everything under /v1 is proxied to the
  // analysis API server-side, which is what keeps the session cookie same-origin and keeps
  // storage credentials out of anything the browser can read.
  async rewrites() {
    return [{ source: "/v1/:path*", destination: `${apiOrigin}/v1/:path*` }];
  },
};

export default config;
