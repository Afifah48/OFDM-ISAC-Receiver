# GitHub publication

Target: `Afifah48/ofdm-isac-receiver`. Project changes belong on `feature/simo-ofdm-isac`. Review and merge the pull request yourself after inspecting the results. Do not push project changes directly to the default branch.

If automatic publication is unavailable, install the official [GitHub CLI](https://cli.github.com/), then run these commands from this repository root. The local repository already contains an empty `main` bootstrap commit and the project commit on the feature branch.

```bash
gh auth login
gh repo create Afifah48/ofdm-isac-receiver --public --description "SIMO OFDM receiver with pilot LS, MRC and shared-waveform MUSIC direction finding"
git -c safe.directory="$PWD" remote add origin https://github.com/Afifah48/ofdm-isac-receiver.git
git -c safe.directory="$PWD" push -u origin main
git -c safe.directory="$PWD" push -u origin feature/simo-ofdm-isac
gh pr create --repo Afifah48/ofdm-isac-receiver --base main --head feature/simo-ofdm-isac --title "Implement SIMO OFDM receiver and shared-waveform MUSIC sensing" --body-file docs/pull-request.md
```

The command-scoped `safe.directory` option trusts only the current directory for that Git invocation; it accommodates ownership differences after sandbox execution without changing global Git settings. Run these commands from the project root in Bash or PowerShell.

`main` is an empty bootstrap so GitHub has a base branch for the pull request. All implementation, results and documentation remain on the feature branch until the PR is approved and merged. If `origin` already exists, use `git -c safe.directory="$PWD" remote set-url origin ...` instead of adding it again. If the GitHub repository already exists, skip `gh repo create`; use an empty repository or review its existing history before pushing. Never force-push over unrelated work.
