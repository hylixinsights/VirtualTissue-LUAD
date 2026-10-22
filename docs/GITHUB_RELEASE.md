# Preparing VirtualTissue-LUAD for GitHub

Destination: [hylixinsights/VirtualTissue-LUAD](https://github.com/hylixinsights/VirtualTissue-LUAD). It was verified as an empty public repository on 30 September 2026. The commands below prepare local files; they do not push commits, upload data or deploy a website.

## Source package

`python scripts/package_release.py` exports an explicit source allowlist to `dist/luad-virtual-tissue-0.2.1.zip`. Source, interface, tests, workflows, English documentation, contracts, the unchanged supplied manual/rulebook and aggregated calibration are included. Raw H5AD/CSV inputs, private runs, request journals, credentials, environments and caches are excluded. `dist/release-manifest.json` hashes each file. The project-wide license remains unassigned as documented in `NOTICE.md`.

## Select and verify one actual recording

Use the completed campaign episode reported in [JEV_CAMPAIGN_5000.md](JEV_CAMPAIGN_5000.md):

```powershell
python scripts/build_site.py --recording outputs/jev-campaign-20260930-5000/LUAD3_B26-S1-seed21-72h-calibrated-jev.luad2.json.gz --output outputs/publication/jev-site --zip dist/VirtualTissue-LUAD-static-replay.zip
python scripts/verify_site.py --site outputs/publication/jev-site
python scripts/prepare_github.py --site outputs/publication/jev-site
```

Run these commands with the project's activated environment. The selected replay contains per-cell Xenium-derived geometry, annotations, local observations and simulated states. It is not anonymized or aggregate-only. It is intentionally separate from the default source-only export. Running or failed checkpoints are rejected. A run stopped by the request ceiling can be exported, with its partial duration and stopping reason displayed accurately. A local-policy preview requires `--allow-local` and remains labeled as local.

The full upload folder is `outputs/github-upload/VirtualTissue-LUAD/`; its archive is `dist/VirtualTissue-LUAD-ready-to-upload.zip`. Both include source and only the selected `site/`. The upload manifest records every selected file and the recording fingerprint. Other local sessions and the API journal remain excluded.

## Preview and publish later

```powershell
python -m http.server 8028 --bind 127.0.0.1 --directory outputs/publication
```

Open `http://127.0.0.1:8028/jev-site/`. The same player works at the repository's GitHub Pages subdirectory because its links are relative. Its embedded atlas/episode are checksum-verified, and `connect-src 'none'` disables network connections in the replay. Downloading the selected episode and opening the provenance page use ordinary same-origin links. No inference key or simulation backend is needed on the hosted site.

After reviewing the prepared folder, the owner can upload it to the repository. To publish the replay, select **GitHub Actions** as the repository's Pages source and manually run **Publish selected LUAD replay**. The workflow first verifies the exact site allowlist and hashes, then deploys `site/`. It has no automatic push trigger and makes no Jev calls. The expected URL after a successful owner-controlled deployment is `https://hylixinsights.github.io/VirtualTissue-LUAD/`; preparation alone does not activate it.

CI uses synthetic fixtures and skips measured-atlas integration tests without private data. Developers supply their authorized source inputs locally to reproduce measured experiments. Refer to [data provenance](DATA.md), [calibration](CALIBRATION.md) and the selected episode's `site/provenance.json` before interpreting its outcomes.
