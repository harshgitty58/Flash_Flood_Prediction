# PRAHAR runbook

How to run, check, deploy and recover the system. Use `C:\Users\HP\anaconda3\python.exe` (or any Python 3.12 env with `requirements.txt` installed).

## Everyday commands

| Task | Command |
|---|---|
| Install | `pip install -r requirements.txt` · `cd web && npm ci` |
| Full rebuild | `python scripts/run_all.py` (28 stages; resume with `--from <stage>`) |
| Re-export only | `python scripts/run_all.py --from export` |
| Tests | `python -m pytest -q -m "not network" tests` |
| Lineage audit | `PYTHONIOENCODING=utf-8 python scripts/audit_pipeline.py` → expect `RESULT: 0 fail, 0 warn` |
| Web (static) | `cd web && npm run dev` → http://localhost:5173 |
| API + web | `python -m uvicorn backend.app:app --port 8000`, then `cd web && npm run dev:api` |
| Research studies | `python -m src.calibration_study` · `python -m src.hysteresis_study` · `python -m src.monotone_study` · `python scripts/terrain_at_gauges.py` |

## Configuration and secrets

| Setting | Where | Notes |
|---|---|---|
| Modelling / QC / tier / impact constants | `params.yaml` | change only through a pre-registered rule; rerun from `data` |
| Allowed browser origins | `params.yaml → api.cors_origins`, or env `PRAHAR_CORS_ORIGINS` (comma-separated) | `*.vercel.app` is allowed by regex |
| Admin token | env `PRAHAR_ADMIN_TOKEN` (never in git) | without it, `POST /admin/reload` returns 403 |

## Deploy
- **Web (Vercel):** project root `web/`, build command `npm run build`, output `dist`. SPA rewrites are in `web/vercel.json`.
- **API (Render):** `render.yaml` (free plan, 512 MB). Set `PRAHAR_ADMIN_TOKEN` and, if the web app calls the API cross-origin, `PRAHAR_CORS_ORIGINS`.
- The free Render instance sleeps when idle: open `/health` about a minute before a demo.
- **After any data or model change:** run `python scripts/make_api_cache.py`, so the API stays within the memory limit.

## When something goes wrong

| Symptom | Check / fix |
|---|---|
| Metrics page blank in API mode | `GET /metrics` must return 200. Re-export (`--from export`), then `POST /admin/reload` with the `X-Admin-Token` header |
| Audit reports a stale stage | rerun from the stage it names (`run_all.py --from <stage>`) |
| `MANIFEST.sha256` mismatch | a raw file changed. If intended, regenerate the manifest (see `tests/test_data.py::test_raw_files_match_manifest`) and say why in the commit |
| Overpass or tile server down (System page red) | the impact build uses cached `data/external/osm_*.json`; the map basemaps fall back to the others |
| CI red on Linux but green on Windows | look for line-ending or path-case assumptions (hashes are LF-normalised for this reason) |
| A gauge shows fake EXTREME rain | check the quarantine rule (`params.yaml → qc.faulty_share / faulty_mm_h`) and that station's QC flags |

## Release checklist (short)
1. Tests green and the audit shows 0 fail.
2. CI green on `main`.
3. Numbers in README and slides match `web/public/data/metrics.json`.
4. No secrets in git.
5. Commit messages carry no tool attribution.
