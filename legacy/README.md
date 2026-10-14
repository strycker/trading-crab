# legacy/ (frozen)

A frozen reference from the retired quarterly pipeline, kept byte-identical (CONTEXT D-14):

- `notebooks/`: the five quarterly notebooks, step1 to step5;
- `data/`: the 36 data snapshots (finviz, FRED, multpl, Grok labels, prepared and standardized; CSV, xlsx, pickle).

Rules: never edited, never read by code, never linted or tested. The pickles are never loaded (a pickle can run
arbitrary code); their CSV twins sit beside them. No new file enters this folder.

The full old tree (code, config, tests) is the annotated tag `legacy/quarterly-final` on `b3e80b3`:
`git checkout legacy/quarterly-final` in a clone to browse it.
