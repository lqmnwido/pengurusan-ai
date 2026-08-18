# Vendored frontend packages

`xlsx-0.20.3.tgz` is the SheetJS Community Edition 0.20.3 package published at:

`https://cdn.sheetjs.com/xlsx-0.20.3/xlsx-0.20.3.tgz`

SHA-256:

`8dc73fc3b00203e72d176e85b50938627c7b086e607c682e8d3c22c02bb99fe8`

The root `package.json` references this tarball with a local `file:` dependency. Normal `npm install` and `npm ci` commands install it automatically; deployment environments do not need to contact the SheetJS CDN.
