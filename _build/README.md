# Build

Encrypted family copy of the "Dani's Updates" Claude page.

    DANI_PW=<password> python3 _build/build.py <data_dir> .

`<data_dir>/site.json` = `{"config": {...}, "posts": [...]}` from the Claude page's db;
`<data_dir>/photos/<assetId>.jpg` = any photo not already in `img/`.
No password or plaintext is stored in this repo.
