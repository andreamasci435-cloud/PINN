# Vercel-only deployment

The default build is a standalone static website. It needs no Python server, external database, API key or paid compute service. Choose Vercel Hobby for a personal, non-commercial portfolio; its usage limits still apply. This does not promise unlimited hosting or unchanged future pricing. See [Vercel Hobby](https://vercel.com/docs/plans/hobby).

## Publish

1. Upload this project to GitHub, including `web`, `canon`, `configs`, `scripts`, package files, `main-2.py`, `requirements-lock.txt`, `LICENSE`, and the four experiment folders listed in `configs/site-archives.json`.
2. Import the repository into Vercel. Select **Other** as the framework, `npm run build` as the build command, and `dist` as the output directory. The included `vercel.json` already configures these.
3. Leave environment variables empty. **Remove `CANON_API_URL` if previously configured.** No Python installation or Docker service is needed on Vercel.
4. Deploy, then test a simulation, archive selection, downloads, Researcher page and the local training dialog on the published URL.

Do not upload `.venv`, `node_modules`, `.env`, `dist` or private documents. Everything in `web/content` is public, including the supplied portrait, CV text and essay. The profile currently uses “Student profile” because the author's name has not been supplied.

## Features

- Interactive visualization, time controls, model/reference comparisons and researcher content remain available.
- New forward simulations run in a browser Web Worker. They use the same conservative spatial equations as Python, with RK4 instead of BDF time integration.
- Real archived PINN results, diagnostics and available result downloads are bundled with the site. They are explicitly archived results, not newly trained models.
- New PINN training runs on the visitor's computer using the downloadable Python training kit. The site gives installation instructions and the selected preset command. It cannot train new models on Vercel or upload local results automatically.
- To publish a newly completed experiment, verify it using the Python CLI, add its folder ID to `configs/site-archives.json`, commit its files and redeploy. The build checks completion and artifact hashes for schema-2 experiments.

## Check locally

```sh
npm ci
npm run build
python3 -m http.server 8766 --directory dist
```

Open http://localhost:8766. This preview needs only a static file server, not the application's Python API. Numerical verification requires the scientific environment:

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check canon tests
.venv/bin/python main-2.py verify results/advanced-confirmation
```

## Optional original Python mode

The original local Python application still supports training and new results. Follow the README's local startup instructions. An optional persistent HTTPS Python backend can be connected by setting `CANON_API_URL` during the frontend build, and `CANON_ALLOWED_ORIGINS` on that backend. That is a separate hosting architecture and is **not required for the Vercel-only edition**. Background training requires one persistent worker and writable result storage; do not package it as a short-lived Vercel function. The Docker configuration is retained for this optional mode and has not been verified on a cloud host.

No public deployment is performed by the build command.
