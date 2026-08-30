/** @type {import('next').NextConfig} */

// Where the /v1 proxy sends requests.
//
// Every environment that is not the deployed one sets API_ORIGIN explicitly:
// infra/docker-compose.yml passes http://api:8000 to the web service. So the default here
// is only ever reached on the Render deployment, and it is the API service's public URL.
//
// It is a literal rather than an env var on purpose. A Render *code* deploy does not
// re-read render.yaml's env vars — only a blueprint sync does — so a service can ship new
// code with API_ORIGIN still unset and proxy every /v1 request to a hostname that does not
// resolve, which fails as an opaque 500. A default that is correct for the deployment
// cannot drift that way. Change this line if the API service is renamed.
const DEFAULT_API_ORIGIN = "https://careerlayer-api.onrender.com";

const apiOrigin = process.env.API_ORIGIN ?? DEFAULT_API_ORIGIN;

// Printed once at boot and once per build. When the proxy 500s, the first question is
// always "which origin did it resolve to", and this puts the answer in the log.
console.log(
  `[careerlayer-web] proxying /v1/* to ${apiOrigin}` +
    (process.env.API_ORIGIN ? " (from API_ORIGIN)" : " (built-in default)"),
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
