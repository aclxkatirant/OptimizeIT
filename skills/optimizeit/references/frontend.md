# Frontend Optimization

**Rule:** Preserve the UI, user experience and behavior exactly. Visual changes require explicit authorization.

## Measurement

| Metric | Tool |
|---|---|
| LCP, INP, CLS, TBT | Lighthouse (CLI: `npx lighthouse <url> --output json`), Chrome DevTools Performance |
| Bundle size | `source-map-explorer`, `webpack-bundle-analyzer`, `rollup-plugin-visualizer`, `vite build` output, `next build` output |
| Re-renders | React DevTools Profiler ("Highlight updates"), Vue DevTools, Angular DevTools |
| Network | DevTools Network tab: request count, transferred size, waterfall |
| Memory | DevTools Memory: two heap snapshots, compare detached DOM nodes and growing objects |

Run Lighthouse several times and use the median; single runs are noisy. Always compare production builds, never dev builds.

## Bundle Size

- **Code splitting:** route-level `import()` / `React.lazy` / `defineAsyncComponent` / Angular lazy routes / `next/dynamic`.
- **Heavy libraries:** whole-library imports (`import _ from 'lodash'` → `import debounce from 'lodash/debounce'`), moment.js locales, full icon sets.
- **Tree shaking blockers:** CommonJS modules, `sideEffects` missing from `package.json`, barrel files that re-export everything.
- **Duplicate dependencies:** the same package bundled in several versions (`npm ls <pkg>`).
- **Polyfills:** targeting very old browsers unnecessarily (check `browserslist`; changing targets changes support → approval).
- **Dev-only code:** debug tooling or mocks bundled into production.

Replacing a library with a lighter one is a dependency change: recommend it, do not apply it without approval.

## Rendering (React example; same principles for Vue/Angular/Svelte)

Unnecessary re-render causes:
- A new object/array/function created on every render and passed as a prop → `useMemo` / `useCallback` (only where it actually prevents work).
- A context value that changes on every render → memoize the value, split contexts.
- State lifted too high → move it down to where it is used.
- An expensive child without `React.memo`.
- Unstable `key`s (index keys on reorderable lists, `Math.random()`).

**Warning:** Blanket `useMemo`/`memo` adds cost and complexity. Apply it only where the profiler shows a costly re-render.

Expensive computation:
- Recomputed on every render → memoize, or move it out of render.
- Long lists (hundreds+ items) → virtualization (`react-window`, `@tanstack/virtual`, `vue-virtual-scroller`). Adds a dependency → approval.

## DOM and Layout

- **Layout thrashing:** alternating reads (`offsetHeight`, `getBoundingClientRect`) and writes in a loop → batch reads, then writes; `requestAnimationFrame`.
- Many individual DOM inserts → `DocumentFragment` or a single update.
- Animating layout properties (`top`, `width`) → `transform`/`opacity`.
- Expensive handlers on `scroll`/`resize`/`input` → throttle/debounce, `passive: true` listeners.

## Event Listeners and Memory Leaks

- Listeners, timers, subscriptions, `IntersectionObserver`/`ResizeObserver` without cleanup on unmount (`useEffect` cleanup, `onUnmounted`, `ngOnDestroy`).
- Global stores that only grow.
- Detached DOM nodes held in closures.

## Network

- Duplicate requests for the same data (several components fetching it) → shared cache/query layer (use what the project already has: React Query, SWR, Apollo, RTK Query, Pinia, etc.).
- Request waterfalls (sequential dependent fetches) → parallelize or fetch on the server.
- Missing compression or cache headers on static assets; no hashed file names for long-term caching.
- Prefetching too much or too little.

## Assets

- Images: proper sizes (`srcset`/`sizes`), modern formats (WebP/AVIF), `loading="lazy"` below the fold, explicit `width`/`height` to avoid CLS. Framework image components (`next/image`, `NuxtImg`) when already in use.
- Fonts: `font-display: swap`, subsetting, preload only critical fonts.
- Converting image files changes assets; confirm quality is visually equivalent.

## Blocking Resources

- Render-blocking `<script>` in `<head>` → `defer`/`async` (check execution order dependencies first!).
- Large inline CSS/JS, unused CSS.
- Third-party scripts (analytics, chat widgets) loaded eagerly → load after interaction or idle. Changing when a third-party script loads can affect tracking → approval.

## SSR / Frameworks

- Next.js: unnecessary `"use client"` boundaries, data fetched on the client that could be fetched on the server, missing caching/revalidation config, `getServerSideProps` where static generation fits.
- Nuxt: `useFetch`/`useAsyncData` keys, payload size.
- Angular: `OnPush` change detection, `trackBy` in `*ngFor` / `track` in `@for`, zone pollution from timers.
- Vue: `v-for` without `key`, deep watchers on large objects, large reactive objects that could be `shallowRef`/`markRaw`.

## Validation

- Production build succeeds, no new console errors.
- Visual comparison of affected pages (screenshots before/after where possible).
- Interaction checks for changed components (clicks, forms, navigation).
- Bundle size and Lighthouse metrics before/after, same conditions.
