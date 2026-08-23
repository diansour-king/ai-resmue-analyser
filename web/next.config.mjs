/** @type {import('next').NextConfig} */
const apiOrigin = process.env.API_ORIGIN ?? "http://api:8000";

const config = {
  // The browser only ever talks to this origin. Everything under /v1 is proxied to the
  // analysis API server-side, which is what keeps the session cookie same-origin and keeps
  // storage credentials out of anything the browser can read.
  async rewrites() {
    return [{ source: "/v1/:path*", destination: `${apiOrigin}/v1/:path*` }];
  },
};

export default config;
