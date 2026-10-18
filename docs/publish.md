# GitHub publication

Repository: [Afifah48/OFDM-ISAC-Receiver](https://github.com/Afifah48/OFDM-ISAC-Receiver). Project changes belong on `feature/simo-ofdm-isac`. Review and merge the pull request yourself after inspecting the results. Do not push project changes directly to the default branch.

The feature branch is based on the repository's existing initial MIT-license commit, preserving its Afifah Khan attribution. The source, documentation and results remain on the feature branch until approval. To upload later changes manually, install the official [GitHub CLI](https://cli.github.com/) and run these commands from the repository root:

```bash
gh auth login
git -c safe.directory="$PWD" remote set-url origin https://github.com/Afifah48/OFDM-ISAC-Receiver.git
git -c safe.directory="$PWD" push -u origin feature/simo-ofdm-isac
gh pr view --repo Afifah48/OFDM-ISAC-Receiver feature/simo-ofdm-isac
```

The command-scoped `safe.directory` option trusts only the current directory for that Git invocation; it accommodates ownership differences after sandbox execution without changing global Git settings. Run these commands from the project root in Bash or PowerShell.

If no pull request exists yet, create one with `gh pr create --repo Afifah48/OFDM-ISAC-Receiver --base main --head feature/simo-ofdm-isac --title "Implement SIMO OFDM receiver and shared-waveform MUSIC sensing" --body-file docs/pull-request.md`. Never force-push over unrelated work.
