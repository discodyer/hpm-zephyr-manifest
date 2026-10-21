# HPM Zephyr Manifest

Lightweight west manifest for an HPM5361 Zephyr workspace.

The manifest imports upstream Zephyr so that its module revisions follow the
selected Zephyr revision. HPM SDK and the HPM Zephyr module are separate
projects.

## Initialize

Set the repository URLs in `west.yml`, then run:

```sh
west init -m <manifest-repository-url> workspace
cd workspace
west update
```

## Freeze a release

```sh
west manifest --freeze -o west-lock.yml
```

Commit the frozen manifest on release branches. Do not publish products from a
manifest that tracks a floating branch.
