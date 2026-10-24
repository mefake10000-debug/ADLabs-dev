# Local processing routes

These Next.js App Router handlers live under the repository-root `app/api/` directory. `src/app/` is a React component folder and is not this repository’s route root.

- `/api/processing/cameras` returns only configured enabled camera IDs and display names.
- `/api/processing/status`, `/api/processing/start`, and `/api/processing/stop` forward fixed requests to EdgeSight `/api/v1/processing/*` through `src/lib/processing-control.ts`.
- They work only in local Next.js development and only with a loopback EdgeSight URL. Production/hosted routes reject control requests; they cannot start a remote edge machine.
- The EdgeSight key remains server-side. These routes never accept arbitrary upstream paths or commands and never control Docker.
- Test shared guard/payload behavior with `npm test`; the route build requires Next.js dependencies.
