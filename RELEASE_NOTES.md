# GPS Learning Studio Release Notes

Stable release candidate for the complete guided GPS learning studio.

## Changes

- Ships the full guided course, editable scenarios, telemetry export, and tested release pipeline.
- Verifies update downloads with SHA-256 checksums before replacing the packaged executable.

## Scenario Migrations

- Saved scenario files using schema version 1 are migrated to schema version 2 when loaded.
- Scenario version 2 adds a metadata envelope while preserving constellation, receiver, simulation time, and speed fields.

## Update Safety

- Release publishing runs tests, builds the Windows executable, smoke-tests it, and attaches checksum sidecars.
