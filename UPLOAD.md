# Upload this prepared repository

Destination: https://github.com/hylixinsights/VirtualTissue-LUAD.git

This folder is prepared locally. No files were pushed and no website was deployed.
It contains allowlisted source and one selected, recorded tissue example in `site/`.
The example includes per-cell Xenium-derived geometry, annotations and local states.
It is not an anonymized dataset. Raw H5AD inputs, other runs, request journals,
credentials, environments and caches are absent.

1. Review `site/model.html`, `site/provenance.json` and `upload-manifest.json`.
2. Commit this folder to the intended repository using your preferred Git client.
3. To host the replay, select GitHub Actions as the Pages source in the repository.
4. Manually run **Publish selected LUAD replay**. The workflow verifies the site
   before deployment. It does not invoke Python simulation or Jev on GitHub.

The expected Pages path is https://hylixinsights.github.io/VirtualTissue-LUAD/.
It becomes available only after your deployment succeeds. You can also host the
contents of `site/` under another subdirectory; links are relative.

The full inspectable trajectory is `site/recordings/episode.luad2.json.gz`.
The embedded player and the downloadable recording are verified to agree.
A request cap is a ceiling; completed simulations may use fewer requests.
