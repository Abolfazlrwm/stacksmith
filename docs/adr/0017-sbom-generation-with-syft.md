# ADR-0017: SBOM generation with syft and grype

- **Status:** accepted
- **Date:** 2026-11-22
- **Supersedes:** —

## Context

Phase 8.1 added Trivy container scanning (ADR-0016). Trivy scans the image
for known CVEs and reports to the Security tab. What is missing is a
**software bill of materials** (SBOM): a machine-readable list of every
package in the image, its version, its license, and its supplier.

An SBOM is the supply-chain artifact. Without it, "what is in this image?"
is a manual `docker exec pip list` or `dpkg -l`. With it, the question is
a `jq` query against a versioned file.

The US Executive Order 14028 (May 2021) made SBOMs a requirement for
federal software procurement. The EU Cyber Resilience Act (2024) moves
in the same direction. Whether or not this kit is subject to those
regulations, shipping an SBOM is the professional baseline.

## Decision

Generate an SBOM for the `stacksmith/app:latest` image on every push to
`main` and on every PR, using **syft** (SBOM generation) and **grype**
(SBOM-based vulnerability scanning). Two formats are produced:

- **SPDX JSON** (`sbom.spdx.json`) — the ISO standard.
- **CycloneDX JSON** (`sbom.cyclonedx.json`) — the OWASP standard.

Both are uploaded as CI artifacts with 30-day retention. Grype results
are uploaded alongside them.

## Rationale

- **Two formats because the ecosystem has not converged.** SPDX is the
  ISO standard; CycloneDX is the OWASP standard. Different tools consume
  different formats. Producing both costs nothing (syft supports both
  natively) and avoids the "which format do you need?" question.

- **Syft over docker sbom.** `docker sbom` is experimental and requires
  a specific Docker buildx setup. Syft is stable, standalone, and works
  on any image without Docker integration.

- **Grype alongside Trivy.** Trivy (Phase 8.1) scans the image directly;
  grype scans the SBOM. They use different vulnerability databases
  (Trivy: NVD + OS advisories; grype: same, but the SBOM-based approach
  catches packages that direct scanning might miss). Two scanners with
  different databases is defense in depth, not redundancy.

- **Artifacts, not Security tab.** Trivy already uploads SARIF to the
  Security tab. Grype results are uploaded as CI artifacts because grype
  does not natively produce SARIF and the operator wants the raw JSON
  for offline analysis.

## Considered alternatives

### docker sbom (experimental)

Rejected. Still experimental, requires buildx, and does not produce
CycloneDX.

### Dependency-track

Rejected. Dependency-track is a full SBOM management platform (server,
database, dashboard). It is overkill for a single-image kit. syft +
grype + CI artifacts is the right weight.

### cosign attestation

Not rejected, but deferred. cosign can attach an SBOM as a signed
attestation to an image in a registry. This requires a registry and a
signing key — both are v0.5 work (when the kit ships to a registry
instead of building locally). For v0.4, the SBOM is a CI artifact.

### Manual `pip freeze` + `dpkg -l`

Rejected. Not machine-readable, not standard-format, and not reproducible
(you have to run the image to get the list). Syft produces the SBOM
without running the image.

## Consequences

- `sbom.yml` workflow builds the app image, runs syft to produce SPDX
  and CycloneDX JSON, runs grype for vulnerability scanning, and uploads
  all three as CI artifacts.
- The SBOM is regenerated on every push to `main` and on every PR. It is
  not committed to the repo (it is a build artifact, not source).
- The operator can download the SBOM from the CI run page and query it
  with `jq` or feed it to a compliance tool.
- Grype results complement Trivy results (ADR-0016). Both are available;
  neither is the single source of truth.
- When the kit moves to a registry-based deployment (v0.5), the SBOM
  should be attached as a cosign attestation. This ADR is reopened then.
