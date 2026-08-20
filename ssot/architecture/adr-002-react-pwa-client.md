# ADR-002: Vite + React PWA (Single Page Application) for Frontend

**Status**: Accepted
**Date**: 2026-06-04
**Deciders**: Antigravity (AI Architect), Clinic Owner, Frontend Lead

## Context

The Clinic Modernization Platform (CMP) must deliver a lightweight, responsive interface optimized for:
1. Patients accessing the portal on mobile devices over standard, sometimes unstable, Nigerian 3G/4G networks (**UG-001**, **NFR-002** - page load < 3.0 seconds).
2. Receptionists and Doctors operating on desktop and tablet computers (**UG-002**, **UG-003**).
3. Local internet outages. In Nigeria, power or ISP drops are common. **NFR-004** mandates that receptionist and doctor scheduling dashboards must cache the current day's appointment lists locally in the browser, allowing read-only access for at least 2 hours during local internet failures.

The project must be completed within 4 months with a cost-effective cloud-hosting budget.

## Decision

We will build the frontend as a client-side Single Page Application (SPA) using **React** built with **Vite**, packaged as a Progressive Web App (PWA). It will utilize **Workbox** for service worker caching and **Dexie.js** (an IndexedDB wrapper) to manage local, read-only offline data storage. The frontend will be deployed as a static build to an AWS S3 Bucket fronted by Amazon CloudFront (CDN).

## Options Considered

### Option 1: Vite + React PWA (SPA + Service Workers + IndexedDB) — Chosen

A pure client-side SPA that compiles to static HTML, CSS, and JS files. The browser registers a service worker to intercept network requests, serve cached shell assets offline, and fetch/query local schedules from IndexedDB.

* **Pros**:
  * Static build allows deployment directly to S3 and CloudFront, reducing infrastructure cost to near-zero and enabling sub-second load times via edge caching.
  * Direct control over the Service Worker lifecycles, making it simple to implement the 2-hour offline read-only scheduling cache (**NFR-004**).
  * High development speed and vast ecosystem of responsive UI library components (Tailwind, Radix, Lucide Icons).
  * Decoupled architecture means API routes can evolve independently on the backend.
* **Cons**:
  * Client-side data fetching requires showing loading states on first load.
  * SEO search engine crawlability is low (not a constraint, as scheduling and clinical records are behind authentication).
* **Estimated effort**: Low. Standard React SPA template with Vite PWA plugin.

### Option 2: Next.js (App Router with SSR) — Rejected

A full-stack React framework utilizing Server-Side Rendering (SSR) and React Server Components (RSC) to render pages on the server before sending them to the client.

* **Pros**:
  * Outstanding initial page load speed for public-facing static pages due to SSR.
  * Integrated API routing and built-in optimization tools (Image, Font, Link components).
* **Cons**:
  * SSR requires running Node.js servers (e.g., on AWS ECS or Lambda), which increases hosting complexity, cloud bills, and failure points.
  * Combining SSR with Service Workers for offline PWA functionality is highly complex, as server components cannot execute when the client is disconnected.
  * Significantly steeper learning curve and slower build times.
* **Estimated effort**: High. Requires node server setup, custom fallback hydration routing, and complex PWA configuration.

## Rationale

The primary operational constraint is local internet reliability (NFR-004). If the clinic's local fiber or cellular internet connection drops, receptionists and doctors must not lose visibility of their schedules. 

A static React SPA compiled with Vite can be completely cached inside the browser using Service Workers. When the network drops, the application shell continues to run locally, loading the cached doctor schedule list from IndexedDB. Since no server-side execution is needed to render the pages, the app remains fully functional in a read-only mode offline. 

Furthermore, static hosting via Amazon CloudFront is highly cost-effective and ensures key pages load within the 3.0-second budget over Nigerian mobile networks.

## Consequences

* **State Synchronization**: We must implement synchronization scripts. The client will fetch schedules daily and write them to IndexedDB. If the client goes offline, the UI will toggle a visual "Offline Mode - Read Only" warning banner.
* **Security**: Sensitive data in IndexedDB must be purged when a user logs out or the session token expires.
* **CORS**: We must configure cross-origin resource sharing (CORS) rules on the backend to allow API requests from the static frontend CDN domain.

## References

* [Clinic Modernization Platform SRD](file:///C:/Users/DELL/Documents/Project/clinic_app/software_requirements_document.md)
* [Vite PWA Plugin Documentation](https://vite-pwa-org.netlify.app/)
* [MDN IndexedDB API](https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API)
