# HPM Zephyr Manifest

Lightweight west manifest for an HPM5361 Zephyr workspace.

The manifest imports upstream Zephyr so that its module revisions follow the
selected Zephyr revision. HPM SDK and the HPM Zephyr module are separate
projects.

The HPM SDK project uses the full upstream tree and is currently pinned to the
`v1.13.0` commit `ccc5ec467a047f3ea85cd2fa4565e91db7135a38`. The `hpm-zephyr`
module is also pinned to a full commit SHA. The development manifest still
tracks upstream Zephyr `main`; release manifests must freeze every project to
an immutable commit SHA.

## Initialize

Set the repository URLs in `west.yml`, then run:

```sh
west init -m <manifest-repository-url> workspace
cd workspace
west update
```

## Freeze a release

Validate the development manifest and the immutable SDK/module pins:

```sh
python3 scripts/check_manifest.py
```

Then create a release lock file:

```sh
west manifest --freeze -o west-lock.yml
```

Commit the frozen manifest on release branches. Do not publish products from a
manifest that tracks a floating branch.
