# HPM Zephyr Manifest

Lightweight west manifest for an HPM5361 Zephyr workspace.

The manifest imports upstream Zephyr so that its module revisions follow the
selected Zephyr revision. HPM SDK, the HPM Zephyr module, and the OpenOCD
backport are separate projects.

The current workspace pins upstream Zephyr `v4.5.0` to commit
`41d10b59730406bbab4ca9f1fbbe9e96aafb4966`. The HPM SDK project uses the full
upstream tree and is pinned to the `v1.13.0` commit
`ccc5ec467a047f3ea85cd2fa4565e91db7135a38`. The `hpm-zephyr` module is also
pinned to a full commit SHA. Zephyr's imported module revisions come from the
selected release's `west.yml`.

## Initialize

Set the repository URLs in `west.yml`, then run:

```sh
west init -m <manifest-repository-url> workspace
cd workspace
west update
```

## Configure the OpenOCD backport

The `openocd-zephyr` project is pinned to commit
`986968d99077e01f48c4dba269342bcd70669fa9`, which contains the HPM XPI flash
driver. After `west update`, build and install it into the workspace-local
tool directory:

```sh
west openocd-setup
```

The command:

- builds the pinned OpenOCD source with FTDI and internal Jim Tcl support;
- installs the executable and scripts under `.tools/openocd-hpm/`;
- sets `build.cmake-args` so future Zephyr builds use that OpenOCD and its
  script directory.

Existing build directories must be reconfigured once:

```sh
west build -d build/<build-dir> --cmake-only
west flash -d build/<build-dir> --verify
```

Check the installation and west configuration without rebuilding:

```sh
west openocd-setup --check
```

The setup command preserves unrelated existing `build.cmake-args` values and
reuses a matching installed build. Use `--force` to rebuild explicitly.
The host must provide the normal OpenOCD autotools, FTDI, USB, and Jim Tcl
build dependencies.

## Freeze a release

Validate all direct project pins:

```sh
python3 scripts/check_manifest.py
```

Then materialize the imported module revisions into a release lock file:

```sh
west manifest --freeze --active-only -o west-lock.yml
```

Commit the frozen manifest on release branches. Do not publish products from a
manifest that tracks a floating branch.
