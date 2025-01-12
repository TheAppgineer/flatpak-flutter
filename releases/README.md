## Determining flutter package urls

Packages normally downloaded at first flutter execution have to be prefetched via a `sources` section in the manifest.

The `.version` files in `flutter/bin/internal/` contain hashes that make up the download paths:

* storage.googleapis.com/flutter_infra_release/flutter/`<engine.version>`/*.zip
* storage.googleapis.com/`<grade-wrapper.version>`
* storage.googleapis.com/`<material_fonts.version>`
