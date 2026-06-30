# Dreamina CLI Manual Spike Guide

## Purpose

The Dreamina CLI can be used for local, manual feasibility checks of real
Dreamina / Jimeng account behavior. It is only a human-operated spike tool.

This guide does not install the CLI, does not run `curl | bash`, and does not
connect Dreamina CLI behavior to the AI Video Workbench provider system.

## Non-Goals

- Do not add the CLI to CI.
- Do not make the CLI a v1.1 provider.
- Do not replace the mock provider.
- Do not call the CLI from the production `generate-video` workflow.
- Do not require contributors to install Dreamina or log in.
- Do not commit credentials, login state, generated tokens, or downloaded
  provider responses containing secrets.

## Safety Risks

The installer at `https://jimeng.jianying.com/cli` appears to target the
Dreamina / Jimeng CLI, but it is still a remote binary installer. Treat it with
the same care as any opaque provider CLI.

Known risks from script inspection:

- It downloads a platform-specific `dreamina` binary from a ByteDance CDN.
- It writes files under `$HOME/.local/bin` by default on macOS and Linux.
- It writes metadata under `$HOME/.dreamina_cli`.
- It can append PATH setup to shell startup files such as `.zshrc`, `.bashrc`,
  `.bash_profile`, or `.profile`.
- It clears macOS quarantine attributes with `xattr` when available.
- It only MD5-checks `SKILL.md`; the binary itself is not verified by a pinned
  SHA256 or signature in the installer.
- It may consume real account quota when generation commands are submitted.
- It uses local login state, so generated credentials or OAuth state must stay
  out of the repository.

## CI Policy

This manual spike must not enter CI. CI must remain deterministic, credential
free, and runnable without a Dreamina account or paid provider quota.

## v1.1 Provider Policy

The CLI is not a v1.1 provider. It can inform future integration planning, but
it does not satisfy the current provider contract by itself because it uses
local OAuth/session state rather than the existing access-key, secret-key,
endpoint, and model contract.

Any future provider work must remain opt-in until it is explicitly designed,
tested, and reviewed as a production integration.

## Isolated Environment Verification

Use a disposable environment first, such as a throwaway VM, container, or
temporary machine account. Do not run the installer on a primary development
machine until the downloaded files and side effects are understood.

Download the installer for review only:

```bash
curl -fsSL https://jimeng.jianying.com/cli -o /tmp/jimeng-cli-install.sh
less /tmp/jimeng-cli-install.sh
```

Do not run this during review:

```bash
curl -fsSL https://jimeng.jianying.com/cli | bash
```

If you decide to test in an isolated environment, prefer a custom install
directory so all writes are easy to inspect and remove:

```bash
export DREAMINA_INSTALL_DIR="$HOME/dreamina-cli-spike/bin"
export DREAMINA_CLI_INSTALL_DIR="$DREAMINA_INSTALL_DIR"
```

Before installing in that isolated environment, read the installer and record
the URLs, target paths, and version metadata.

## Recording SHA256

Record checksums for every downloaded artifact before running it.

Installer checksum:

```bash
shasum -a 256 /tmp/jimeng-cli-install.sh
```

If you manually download a platform binary for inspection, record it too:

```bash
shasum -a 256 /path/to/dreamina
```

Save the output in a local spike note outside the repository. Do not commit
provider binaries, local notes containing account details, or login artifacts.

## Viewing CLI Help

After installation in an isolated environment, inspect help before running any
real command:

```bash
dreamina -h
```

For any subcommand, inspect its exact flags first:

```bash
dreamina image2video -h
dreamina text2video -h
dreamina query_result -h
dreamina user_credit -h
```

Do not assume that flags, model names, durations, ratios, or resolutions are
shared across subcommands. Use the installed CLI help as the source of truth.

## Login And Account Credit

The CLI uses local login/session state. If help-only inspection is complete and
you intentionally want to test real account behavior in the isolated
environment, log in using the CLI's documented login flow:

```bash
dreamina login
```

For headless environments, inspect help first:

```bash
dreamina login -h
```

Check account credit before submitting any generation task:

```bash
dreamina user_credit
```

If the command reports unavailable credit, account authorization requirements,
or quota limits, stop the spike and record the failure reason.

## Submitting image2video

Only submit an `image2video` task after:

- The environment is isolated.
- The CLI help has been inspected.
- Login is complete.
- Account credit has been checked.
- The user has explicitly accepted possible credit usage.

Inspect the exact command surface:

```bash
dreamina image2video -h
```

Then run the smallest possible task using the flags shown by that help output.
The exact flags are CLI-version dependent, so keep the command in the spike log
instead of hardcoding it into application code.

Example template:

```bash
dreamina image2video \
  <image flag from help> /absolute/path/to/keyframe.png \
  <prompt flag from help> "short low-risk motion prompt" \
  <duration/model/ratio flags from help>
```

Treat submit as successful only if the output includes:

- a non-empty `submit_id`
- `gen_status` of `querying` or `success`

If `gen_status` is `fail`, record the provider failure reason and do not retry
blindly.

## Querying And Downloading Results

For asynchronous tasks, save the returned `submit_id` and query it separately:

```bash
dreamina query_result --submit_id=<submit_id>
```

To download media in the isolated environment, inspect help first and then use a
dedicated output directory:

```bash
dreamina query_result -h
mkdir -p /tmp/dreamina-spike-results
dreamina query_result --submit_id=<submit_id> --download_dir=/tmp/dreamina-spike-results
```

Record:

- command used
- CLI version
- account region or session label, if visible and non-secret
- `submit_id`
- final status
- local result file path
- SHA256 of downloaded media
- whether any credits were consumed

Do not commit downloaded media unless it is explicitly approved as a safe,
non-sensitive fixture.

## Fit For AI Video Workbench

The CLI can help answer manual feasibility questions such as whether a real
Dreamina account can submit an `image2video` task and download a result.

It is not suitable as the v1.1 temporary provider because:

- It depends on local login state.
- It may consume real quota.
- It is not deterministic enough for CI.
- It does not match the existing Jimeng REST provider contract.
- It requires an opaque binary and local installation side effects.

Keep CLI exploration separate from provider contract tests and production
workflow code.
