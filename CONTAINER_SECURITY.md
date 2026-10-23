# Container security and launch contract

The Dockerfile defaults to a non-root service user. Application code, runtime
libraries, and executables are owned by root; only designated state/cache
paths are service-owned. Configuration and secrets must be supplied at runtime.

The checked-in Compose definition applies a read-only root filesystem, drops
all Linux capabilities, enables `no-new-privileges`, and supplies a writable
`/tmp` with `noexec,nosuid,nodev`. It retains Docker's default seccomp profile
and network namespace. Do not launch with privileged mode, host namespaces,
unconfined security profiles, or a Docker socket mount.

These runtime restrictions are applied when creating the container; building
or running the image alone does not enforce them. Writable data and readable
credentials remain accessible to the service if it is compromised. `noexec`
on temporary storage does not prevent an interpreter from reading scripts.
CPU, memory, and process limits are deployment policies and are intentionally
not specified here; they do not establish the application's authority boundary.

Apply the definition during the separately authorized deployment. Existing
containers are not changed by editing these files. Preserve existing site-local
configuration, credentials, proxy integration, and persistent data when adopting
it. An existing volume or bind mount must already be writable by the documented
service UID/GID; rebuilding does not change existing volume ownership.

## Service configuration

Copy `config.yaml.example` to a site-local `config.yaml` (or set
`CONFIG_FILE`). The image binds port 9010 inside the container; Compose publishes
it on loopback. UID/GID is `10001:10001`. Caches are in memory; Gunicorn worker
temporary files use `/tmp`. No persistent writable mount is needed.

## Minimal production runtime

Production images contain no shell, package manager, compiler, or download CLI.
Startup and healthchecks use executable/argument arrays. Builder and operator
stages may contain tools; those stages are not the production runtime. The
read-only filesystem, dropped capabilities, and privilege restrictions in
Compose remain required. Interpreter APIs, accessible credentials, shared
libraries, and allowed network connections remain part of the attack surface.
No outbound network restriction is implied by this image change.

After building the production image, check its actual exported filesystem:

```sh
python3 tools/container/check-image.py IMAGE
```

The checker runs outside the application image. It rejects shell-based
healthchecks, root execution, common utility binaries, unexpected executable
ELF payloads, non-root-owned application files, and selected non-service files.
It prints the image ID and executable/library inventory for review. It does not
claim that retained libraries are vulnerability-free or that every reachable
interpreter operation is safe.

The runtime filesystem is assembled from the existing pinned distribution by
`tools/container/assemble-rootfs.py`. Preserve native-library and rendering
compatibility when changing its allowlist; test the final image, not just its
builder. The assembler is not shipped in the production image.

Unit-test the inventory gate with `python3 -m unittest discover -s
tools/container -p 'test_*.py'`. The native runtime repositories include
additional dependency-discovery and runtime-exclusion tests.

## Validation (2026-10-21)

Compile checks and `uv run --no-project --with-requirements requirements-dev.txt
python -m pytest` passed (11 tests). The final shell-free image passed health,
status, ping, and menu HTTP checks, plus verified outbound HTTPS through both requests and the standard library.
The final image build asserts that standard TLS trust paths are present.
Unused GUI/test extensions, Python build objects, package installers, and the
associated setuptools startup hook are excluded together.

The final production filesystem passed the exported-image security gate. Its
negative unit tests passed (8 tests, plus 5 assembler tests for native images).
Node/Python runtime probes verified non-root execution, a read-only root,
zero effective capabilities, NoNewPrivs=1, seccomp filtering, and writable
temporary storage. State tests used disposable mounts, not production volumes.
No image build or test constitutes a deployment. No deployment was performed.

Local unpacked image size: 230.2 MiB before minimization,
95.1 MiB after. Size reduction is descriptive; the security
properties are the retained authority and executable contents.

## Functional image validation (2026-10-21)

Run `python3 tools/container/functional-check.py IMAGE`. The final image ran
Gunicorn with the production worker/thread settings against local HTTP fixtures.
ZIP lookup, NWS points/station/observation/forecast/alert clients, weather/current/
forecast/alert-detail requests, valid Cisco XML, repeat-request caching, existing
PNG assets, and Pillow-generated PNG decoding passed. Upstream providers were
fixtures; this does not certify current live NWS or ZIP-provider responses.

These checks use non-root containers, a read-only root filesystem, all
capabilities dropped, `no-new-privileges`, and disposable writable temporary
storage. No shell or test framework was installed into a production image.
Passing these paths is evidence of runtime compatibility, not exhaustive
workflow or production acceptance. No deployment was performed.
