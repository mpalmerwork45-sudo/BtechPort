# AI use and implementation provenance

BtechPort uses **AI-assisted reverse engineering, implementation and testing**,
including **OpenAI Sol 6.1 and Astra**. Human contributors direct the work,
report discrepancies from playing the original game, set priorities and review
results. This disclosure describes the project workflow; it does not attribute
every file or finding to a particular model.

AI is used to investigate file formats and original machine-code routines,
interpret emulator observations, write the independent C implementation,
develop extraction and comparison tools, and maintain documentation. It can
make mistakes. A generated explanation or passing native-only test is not proof
that the port matches the original.

The original DOS executable and repeatable observations are the behavioral
authority. Bounded original-routine tests record their prerequisites, numeric
results and source hashes. Screen comparisons record the region actually
compared. Findings distinguish **VERIFIED**, **INFERRED**, **APPROXIMATE** and
**UNKNOWN**; broader behavior remains unverified unless covered by evidence.

The port **does not use the original game's source code**. It is an independently
written implementation informed by executable behavior, original data and the
substantial reverse-engineering research credited in the
[README](../README.md#acknowledgements) and [research audit](RESEARCH_AUDIT.md).
Consulting those sources is not a claim of a formal clean-room process.

Each runner must supply the original DOS installation. Derived runtime caches,
extracted text, RAM dumps and captures stay in ignored local directories.
The user-authored Last Beacon revision committed in `bed75e9` includes editable
tiles copied from the supplied CHI atlas; its `EDITOR.json` records those
sources and subsequent editing metadata. The GPL-3.0 license for this project's
authored code and documentation does not license that source artwork, the
original game or third-party dependencies.

The optional [Updated CHI roster](../content/updated/README.md) adapts numerical
unit records from MegaMek's mm-data contributors. Its sources, CHI adaptations
and separate CC BY-NC-SA 4.0 data license are recorded alongside the pack.

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for current scope and
[TESTING.md](TESTING.md) for repeatable verification procedures.
