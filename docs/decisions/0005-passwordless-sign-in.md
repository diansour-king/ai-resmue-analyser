# 0005. Sign-in is a one-time emailed link, and there are no passwords

Status: accepted
Date: 2026-08-23

## Context

Section 4 of the build specification chose Auth.js with an email magic link, and gave the
reason: no password storage, no OAuth app review, minimal surface.

The phase 2 brief asks for `/login` and `/signup` as separate routes. Those are the shape of a
password product: with a magic link, signing up and signing in are the same interaction with a
different first step.

The two instructions are not obviously compatible, and the difference is not cosmetic. One of
them stores password hashes and the other does not.

## Options considered

**Email and password.** Matches the two route names most directly. Rejected: it means storing
password hashes, building reset flows, rate limiting a guessable credential, and owning a
breach class this product has no reason to own. The specification rejected it for those
reasons and nothing has changed.

**Auth.js in the Next.js app.** As literally specified. Rejected for now: Auth.js would own the
session while FastAPI owns the database and every authorisation decision, so the two would need
a shared secret and a second notion of identity. That is the "second authentication system" the
brief explicitly forbids.

**One-time link issued and verified by the API, with both routes kept.** Chosen.

## Decision

`/signup` and `/login` both exist and both collect an email address. Signup creates the account
if it is new; login does not. Both issue a single-use token, and following the link exchanges it
for an httpOnly session cookie.

FastAPI owns users, tokens and sessions, because it owns the database and makes every
authorisation decision. Next.js proxies `/v1/*` to it server-side, so the browser talks to one
origin, the cookie is same-origin with no CORS, and the API host is never in a URL the browser
can see.

Only hashes are stored, for both login tokens and session tokens. A database dump must not hand
anyone a working credential, which is the same reason a password would be hashed if this system
had passwords.

`POST /v1/auth/login` returns the same 202 for a known and an unknown address. Answering
differently turns the endpoint into a test for whether a given person has an account here.

In development the link is returned in the response so the flow works with no mail server. The
setting that enables that is named `environment` and defaults to `production`, so a deployment
that forgets to configure it withholds the link rather than exposing it.

## Consequences

- There is no password to store, leak, reset, or rate limit.
- Sending real email is not built. Until it is, `ENVIRONMENT=development` is the only way to
  sign in, and that is a hard blocker for deploying this to anyone but ourselves. It is the
  first item in the phase 5 prerequisites.
- A sign-in link in an inbox is a bearer credential for fifteen minutes. That is the accepted
  trade for having no password, and it is why the token is single-use and short-lived.
- Auth.js is not used. If a future phase needs OAuth providers, this decision is what would be
  revisited, and the session table is the seam.
