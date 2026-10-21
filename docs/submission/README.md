# Freeze and submission packet

This is a reviewable local preparation packet, **not a completed or submitted hackathon entry**. The user selected MIT. No article, video, Devpost submission, hosting resource, or provider request was published/executed by this milestone.

## Local artifacts

| Artifact | Location | Scope |
| --- | --- | --- |
| Complete project README | `../../README.md` | Setup, features, architecture, screenshots, limits, team/license |
| Technical docs | `../architecture.md`, `../safety.md`, `../demo.md`, `../development.md` | Implemented behavior and exact operation/verification boundaries |
| Editable architecture diagram | `../assets/architecture.svg` | Repository-native vector source |
| Architecture export | `../assets/architecture.png` | PNG export for sharing |
| Eight 3:2 screenshots | `../assets/screenshots/` | Visibly mocked local UI rehearsal |
| Captioned rehearsal video | `../assets/rehearsal.webm` | Silent local walkthrough; inspected duration/hash in manifest; not final live footage |
| Capture manifest | `../assets/capture-manifest.json` | Mocked provider/search/cluster provenance, screenshot dimensions, inspected video hash/duration |
| Sample RCA | `../assets/rehearsal-rca.md` | Explicitly mocked; not acceptance evidence |
| DEV.to draft | `article.md` | `published: false`; no invented provider feedback |
| Devpost draft | `devpost.md` | Proposed fields plus unresolved URL/team/feedback entries |
| Acceptance template | `golden-path-results.json` | Pending, zero accepted live runs |
| Release gates | `readiness.json` | Passed and remaining prerequisites are explicitly recorded |

## Verification commands

```bash
python3 scripts/check_submission.py
python3 scripts/check_submission.py --release-ready
```

The first command validates local files, relative Markdown links, screenshot dimensions, rehearsal provenance, and inspected video hash/duration. The second additionally checks declared release evidence and is **expected to exit 1** until unresolved gates pass. It does not independently attest a remote deployment, model request, or account publication.

After regenerating the video, inspect its actual media metadata rather than copying an old duration:

```bash
python3 scripts/check_submission.py --inspect-video /absolute/path/to/ffmpeg
```

## Release gates

- [x] Real Nebius/Nemotron connectivity and runtime reasoning verified with authorized quota.
- [x] Conditional Tavily branch verified live when requested.
- [x] Five distinct successful real OOMKilled product runs, with reviewed evidence and healthy lab reset.
- [x] Docker build/runtime smoke on an equipped machine.
- [ ] Actual public deployment URL, HTTPS/CORS/SSE/assets, and judging access checked.
- [x] Public repository visibility confirmed; MIT and dependency notices checked.
- [x] Final live demonstration publicly uploaded and verified online at 2:31; the repository WebM remains rehearsal-only.
- [ ] Team roster, attribution, representative consent, project-start declaration, and actual tool feedback confirmed.
- [ ] Approved DEV.to article published and actual URL added.
- [ ] Devpost fields reviewed, final links supplied, and submission sent through the team's account.

The guarded acceptance recorder and exact demo storyboard are in [demo.md](../demo.md). The current recorded test/capture evidence is in [state of play](../INCIDENTZERO_STATE_OF_PLAY.md). Keep Oct 25 as the internal engineering deadline; do not use the Oct 30 submission date as extra feature-development scope.
