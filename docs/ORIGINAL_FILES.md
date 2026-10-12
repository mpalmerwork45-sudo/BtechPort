# Original files — M0, 2026-10-11

**VERIFIED:** 88 files, 641,365 bytes, all in one directory; no identical-content duplicate groups. No manual, README, configuration file or alternate game executable is present. This is the supplied corpus, not a claim that it is a complete retail distribution. Provenance against a separate retail image is **UNKNOWN**. Regenerate this inventory with `python3 tools/inventory.py`; verify the immutable trees with `python3 tools/reference_guard.py verify`.

## Executables and loading

`BTECH.EXE` (152,429 bytes) is the correct game executable. Its embedded version string is **VERIFIED** `Version 1.03`; it boots without patching in DOSBox 0.74-3, using a working copy. `$VERIFY.EXE` (16,281 bytes) is another DOS MZ executable; its exact role is **UNKNOWN**, and it was not needed for the observed run. There is no `UNBTECH.EXE` in the original directory.

`BTECH.EXE` uses the 16-byte `RB` EXEPACK variant: packed header at file offset `0x23870`, initial packed CS:IP `2367:0010`, recovered entry relative CS:IP `187F:2D82`. The independently extracted **unrelocated load image** is 247,216 bytes, SHA-256 `100f0df244e4b0c8693d1b5013fb073f486b35d6f5c538ecd53d03f85ed54bfa`. `tools/exepack.py` reads the binary without modifying it; it does not construct a replacement DOS executable. Packed disk offsets, image offsets, Reko's load base `0800`, and live DOS load segments must be distinguished. The observed DOSBox load segment is `01A2`, not a portable fixed address.

Original launch: `python3 tools/reference_session.py --script tools/reference-movement.json`. The harness mounts only ignored `work/dos/`, selects VGA and hard disk, uses normal CPU core at 10,000 cycles, records inputs, captures frames and reads its child emulator's memory. Xvfb keeps the session off the user's desktop. Every run is bounded and closes automatically. DOSBox, Xvfb and small supporting packages are extracted under `local-deps/`; no system installation or reference modification was performed. Spice86's matching source/runtime and dotnet are missing locally. Details are in [TESTING.md](TESTING.md).

## Resource census and format findings

| Group | Count | Evidence / limits |
|---|---:|---|
| BLD | 26 | All converter raw-byte round trips pass; Citadel decryption/menu/Hall/first Katrina visit/repeat/exit are **VERIFIED**, broader control flow remains **INFERRED/UNKNOWN**. |
| MTP | 15 | MAP1–14 have a **VERIFIED** 541-byte header and 8×8 block order; MAP15 is a different 768-byte raw map. |
| ICN | 5 | **VERIFIED** signed-RLE output is 32,000 packed bytes / 64,000 pixel indices per file. |
| CMP | 7 | Same signed-RLE; format 2 uses column-major packed bytes. |
| ANM | 22 | O0–O21; independent XOR-delta decoding and bounded launch/dream/recruitment/loss/portrait dispatch are **VERIFIED**; other playback contexts remain open. |
| GAME | 6 | GAME1–6, all **VERIFIED** 3913 bytes. Original save semantics **UNKNOWN**. |
| Save backups | 3 | GAME1.bak, GAME4.bak, GAME5.bak, also 3913 bytes. |
| EXE | 2 | BTECH and $VERIFY; both lengths match their MZ declared size. |
| Other | 2 | DEMOFILE (1023 bytes), role **UNKNOWN**; WWOODBT.SIF (4352 bytes), title music **VERIFIED** from original file load and PC speaker interrupt trace. |

MTP dimensions: MAP1/2/11/14 are 64×64 (4637 bytes), MAP3–10 are 32×32 (1565 bytes), MAP12/13 are 8×8 (605 bytes). MAP15 is 32×24 according to secondary format evidence, not accepted by the local-map parser. All MAP1 tile IDs fit the 250-tile BTTLTECH sheet.

ICN/CMP's initial little-endian size word counts bytes **after the size word**, including the format byte: `file_length - 2`, not `file_length - 3`. Positive runs copy that many literal bytes; negative signed runs repeat the next byte; zero introduces a 16-bit repeat count and value. All twelve files meet the size and decoded-length checks. Format-1 ICN tile pixels can be viewed as 16×4000. The standard EGA palette matches the secondary extraction PNG; the original MAP1 VGA display additionally maps resource index 5→EGA 9 and index 9→EGA 1, verified against captured frames.

Linux paths must preserve case and spaces: use `--data "Original DOS"`, or an absolute quoted path. The native M2b loader expects exact uppercase `MAP1.MTP`, `BTTLTECH.ICN` and `CITADEL.BLD`; the backup suffix is actually lowercase `.bak`. Missing resources produce diagnostics. Proprietary files, extracted pixels, screenshots, RAM dumps and local dependencies are excluded by `.gitignore`. See [Citadel evidence](M2_CITADEL_EVIDENCE.md) and [Katrina evidence](M2_KATRINA_EVIDENCE.md) for the verified BLD subset.

## Complete manifest

Apparent formats below are scoped by the confidence statements above. Full headers and additional metadata are in [original-manifest.json](original-manifest.json).

| File | Bytes | SHA-256 | Apparent format |
|---|---:|---|---|
| `$VERIFY.EXE` | 16281 | `b410e7135dc48523452dfd14f2288a1374f9d26f6774337a554190811e1a856d` | DOS MZ executable |
| `ANIMATE.ICN` | 3613 | `499269ac20d6e091cfb886280af17c2edd0d0343e80ea293f5ed767c22f78a0b` | packed nibble graphics / signed RLE |
| `ARENA.BLD` | 3957 | `157f2981bff60b1fc6a8b76a09fe74c85b01cd1bdfdde70ad1acd8c87ba266fa` | BLD script / cipher |
| `ARMOR.BLD` | 3388 | `a57c31a718aa7ac16ea83c02e7ae6e7abaf3c4c1ba7de4697bc5c11abb75423f` | BLD script / cipher |
| `BARRACK2.BLD` | 362 | `24929e3e4a7e47e29be5b1c13449f21282d32c12070256b26bfe4c6fb4284df7` | BLD script / cipher |
| `BARRACKS.BLD` | 2990 | `878c7b829710adaa9cb91fbf9795e8486478418eaa63cd5f8d277e2a25579eb8` | BLD script / cipher |
| `BTBORDER.CMP` | 287 | `a4095d7ef9fd31deb470a5932057324ef447476ce5a31ae1aa27f74eb65eeea7` | packed nibble graphics / signed RLE |
| `BTECH.EXE` | 152429 | `15a1712682cf1fe50ca9e6a68a4b31d3bef7912401915edf7bb6242be193562a` | DOS MZ executable |
| `BTSTATS.CMP` | 12637 | `ab40500848638f687b423a2dc115bed631f178faa966073efb50fb08fe4a1ddd` | packed nibble graphics / signed RLE |
| `BTTITLE.CMP` | 27488 | `6907a167d963509b3fc6067224c12d420f042e2ed64a06b426cb1572a810764d` | packed nibble graphics / signed RLE |
| `BTTLTECH.ICN` | 28861 | `857ad418de7c834c6bd0a301b6fc51c9424625d1ee332c0b0888bef59e417c0d` | packed nibble graphics / signed RLE |
| `CITADEL.BLD` | 4330 | `dc4e215ba2c2d6be535c837f96e4158189d9e4c033df6648c9c21c264bfb817b` | BLD script / cipher |
| `CLOTHES.BLD` | 915 | `cd2b597fcf4a3397c069a3789a5b570b2ccc3e17be1b7f92b05b092d0be94bb6` | BLD script / cipher |
| `COMSTAR.BLD` | 2267 | `d329d8811dae70997ed928d9952aa602a3a9bb841222ee1c544509c0ac3d1223` | BLD script / cipher |
| `DEMOFILE` | 1023 | `b84b7244daee52f6d118f946e474df047141ee4b4d7e0d1102f8991c19948ca3` | UNKNOWN |
| `DESTRUCT.ICN` | 29706 | `0d7283b1b3a5791c088a067919d99d78d5236c84f2c5247a08ec00b8491c328e` | packed nibble graphics / signed RLE |
| `ENDMECH.BLD` | 1022 | `f7e93776db8194c6ebe13a6198d6562480741c310d98fa845aeb4eef3866f316` | BLD script / cipher |
| `ENDMECH.CMP` | 16215 | `f0b206ddb059d3ceb8b085da68f182413a02a801d9d73692e01ab67dc58303f4` | packed nibble graphics / signed RLE |
| `ENTRANCE.BLD` | 794 | `59dc8efd8e22e97da9645f3997ce894fddecd1da08de68659d67312f9dff62cf` | BLD script / cipher |
| `FINDIT.BLD` | 722 | `dff5a5fe6bb133b3eacc3f3e644a13a7c4965ab5eac942c28384fe44745a6480` | BLD script / cipher |
| `FROB.BLD` | 3548 | `ce2b333d22d270596cbe3321f4d8fdb8157d21be456535ecd8ef501406f5cd0c` | BLD script / cipher |
| `GAME1` | 3913 | `fc36ce4bb1d32094b8808e067183df922959a621f43550623e74bdb5beeae209` | original game save; semantics not round-trip verified |
| `GAME1.bak` | 3913 | `d09a3d166c9249f065de8990289e23346dd95b06fb5dbb0f34db8082fbb96856` | original game save; semantics not round-trip verified |
| `GAME2` | 3913 | `92cb809d163a3fb77d81a5f195120aaba2c15ff67da9cf10b573d647a23fbd19` | original game save; semantics not round-trip verified |
| `GAME3` | 3913 | `c4486966493384015c90abe7b1dcb74c68975cc7680efb2d7b4a573da59bce13` | original game save; semantics not round-trip verified |
| `GAME4` | 3913 | `b4d8cb6b7b8dd6fc909cd0bf7e8d992c77580f9ee336b117caea8316d2c2bba7` | original game save; semantics not round-trip verified |
| `GAME4.bak` | 3913 | `532d88798316fda6ef0c4eaaebdf1c1130f398e02c17d0dd1ba0a2caf7377e91` | original game save; semantics not round-trip verified |
| `GAME5` | 3913 | `43be65602bfa9f3716a898b755ac06ab83a8de5cf7e5e626427c6659e1c2c6be` | original game save; semantics not round-trip verified |
| `GAME5.bak` | 3913 | `11ac45256903e1ad12e8dafce4db7ea72604c7b99c6cf5a2fa3c67b55b5d511b` | original game save; semantics not round-trip verified |
| `GAME6` | 3913 | `6536cf9b50e8449302b3d6646c6b736a6b43c515d7d9ebecd911cea2a982463a` | original game save; semantics not round-trip verified |
| `GARAGE.BLD` | 1686 | `3aae8a8931f16e63414ab595a069f44a4b436fac1c605f13eb83269d6ce23d37` | BLD script / cipher |
| `HOSPITAL.BLD` | 4581 | `1ef9e77d0c762a38e7d4e37bb2a666e7ba90f9bca77f37f64a309c3619c5b26a` | BLD script / cipher |
| `HUT.BLD` | 8501 | `1e44d727c00214f685498433b4c062d74969a43fba9aa30b79b40fe0b53b5a68` | BLD script / cipher |
| `INFOCOM.CMP` | 6983 | `9158ff357de4b3aa0f1004c8b75fed9393f94b0a367c75dc6b3325a63ea4d30b` | packed nibble graphics / signed RLE |
| `INSTRUCT.BLD` | 565 | `a6f11bd55102231f6931a0e74368d49ffff2d281749a02c63a798eb979d731d4` | BLD script / cipher |
| `JAIL.BLD` | 4297 | `c73328fb9f9ca51f6e05a4bee53054afed518a1dda51810b3ee967034cbd93b0` | BLD script / cipher |
| `LOUNGE.BLD` | 1827 | `3efec6eb3a03b2844c8383462351ae2e4eedb4a9713b6f9c0d3c412097a76ecf` | BLD script / cipher |
| `MAP.ICN` | 12135 | `583c1ba616fc15c549e4420cb942111cd2e1f73497a1642c51992d82488c5e3b` | packed nibble graphics / signed RLE |
| `MAP1.MTP` | 4637 | `67af9479e4d54ca0c93d709b7682f80ddea04265f01aadca0c1f1db97f15542c` | MTP header + tiles |
| `MAP10.MTP` | 1565 | `40a46df6a54051c1219beedf7e66a66f814449867ca8ad692f118f1a90e8bf80` | MTP header + tiles |
| `MAP11.MTP` | 4637 | `52313ba5880d97a694e11712d93009b0d653ad23fe809569f7504c5dfdf90dd6` | MTP header + tiles |
| `MAP12.MTP` | 605 | `c92e55765743919f5085271576f66fdceb8c23483c3c633d2d55bbf7258d3e46` | MTP header + tiles |
| `MAP13.MTP` | 605 | `575290fe0d1f4324fa009ac42093aca25aeb1223430f792885cd158a91421099` | MTP header + tiles |
| `MAP14.MTP` | 4637 | `7c9d76d1d49f1d812805a548e7d8c94c3cb481b08fb490e6a72908e4cd8384e3` | MTP header + tiles |
| `MAP15.MTP` | 768 | `a03d1fa0cfe8f80d69da841473c1b714363e2f8ca8bdea6cc4149f475c093b78` | raw 32 x 24 star map (reference interpretation) |
| `MAP2.MTP` | 4637 | `a4ad5bd88b6b26c3fa65665973d358d669f97f54795c09049373ae7472a5f26d` | MTP header + tiles |
| `MAP3.MTP` | 1565 | `300c1d3c3f2e526f6240b20a980d9cd9997f2353b91226fb8b992d4cff5aaa60` | MTP header + tiles |
| `MAP4.MTP` | 1565 | `66b814334f34805f5cde2adc523c58b2507b4318b2765f20ec257f12edbba11c` | MTP header + tiles |
| `MAP5.MTP` | 1565 | `833d47be7a7a1b2d60cb15fc46cd006748c7a612a121b26c321c985078abb071` | MTP header + tiles |
| `MAP6.MTP` | 1565 | `bfc5e5620ee2d28759927f782a02cbbf5b79bc4eef13f9a9c9e3c619c9eaab2e` | MTP header + tiles |
| `MAP7.MTP` | 1565 | `ceee2038a0ac23ba873713f83d6c7b62c5ee678ff3fdfccc8b25fac7ac348ce4` | MTP header + tiles |
| `MAP8.MTP` | 1565 | `3e2779d7802346adabb41a15f164e459ceeeac69d743cfe85a92c22c5b385962` | MTP header + tiles |
| `MAP9.MTP` | 1565 | `336051abfeff17db28953b241bf4764b48a5b986950cb9a291664f71cdf491eb` | MTP header + tiles |
| `MAYOR.BLD` | 5896 | `5cfa6d15cf042d5e1b74538732cfe7c8b2577e0f26985877289f101c17273f56` | BLD script / cipher |
| `MECHSHAP.CMP` | 16918 | `861545376ecff306fecf960cfb61f931dda61a640ec1c9f417a4a5108e5edc05` | packed nibble graphics / signed RLE |
| `O0.ANM` | 5120 | `aafe6dda17dac9f57628781a056b75a9ffbedcb647a7830e47864e435e128953` | ANM XOR-delta animation (reference interpretation) |
| `O1.ANM` | 5888 | `c53ba5d57f5d20ec19b71950eae7910ce1fb8ea91e115718f252375cc495d061` | ANM XOR-delta animation (reference interpretation) |
| `O10.ANM` | 6144 | `9c23ab69b372efdc64d0f94ac0d75fc4985a94f8fbb4f30ac631ee731e0895c3` | ANM XOR-delta animation (reference interpretation) |
| `O11.ANM` | 3584 | `bfdb2e262b5e4802206c83277c38860e2a02f1713fc12d67cce857067f1945cb` | ANM XOR-delta animation (reference interpretation) |
| `O12.ANM` | 7296 | `a69831177c7774da9649bde125b7dd8a2da5171a4e2ba2815e8be4b6bf2acc6e` | ANM XOR-delta animation (reference interpretation) |
| `O13.ANM` | 5248 | `6a7b2cd81ae716b264452e56ddc93a88757338854129d3fcada7958d9e932fdc` | ANM XOR-delta animation (reference interpretation) |
| `O14.ANM` | 4992 | `022eea23e2ecce7c1a8a784d2c3bb12f88befec2de64a306ce08046f5f2a6a6b` | ANM XOR-delta animation (reference interpretation) |
| `O15.ANM` | 12800 | `d85b711c6597ecbe9c63270330cb72f77d22204915e2fbd3a84f88c5f12b5d1e` | ANM XOR-delta animation (reference interpretation) |
| `O16.ANM` | 8320 | `1616ef4381527eda7ee0d6e7b6e1d1258ea12076f08885884a06cbd1427facb6` | ANM XOR-delta animation (reference interpretation) |
| `O17.ANM` | 3200 | `31a9a28bbf05e704bd6d37caa1d2112b83ab28de9bd7cd5f1d7cc2a222641a02` | ANM XOR-delta animation (reference interpretation) |
| `O18.ANM` | 3456 | `2b8c6293eafc7be7b7e3c84947d1ccbd5128a6188efef48945aec6241df34514` | ANM XOR-delta animation (reference interpretation) |
| `O19.ANM` | 3840 | `eb1b8aefbe4e9394eb3e5cb64a35d125a87c2b768b99c9ae5749fc5e089ddf03` | ANM XOR-delta animation (reference interpretation) |
| `O2.ANM` | 6400 | `db1b0959cdec9bd41bf212561f8a4af79d0ff02fb685e74a8339668a7fb31a86` | ANM XOR-delta animation (reference interpretation) |
| `O20.ANM` | 3200 | `b43c4516af8a9570e751a4dc00a9343e099767c90a542b533e6b375dba07e9d7` | ANM XOR-delta animation (reference interpretation) |
| `O21.ANM` | 3328 | `3a2eb3655a77f2a040e471783a376713ac5d23f3651425ea33a9d017142cca5a` | ANM XOR-delta animation (reference interpretation) |
| `O3.ANM` | 6912 | `68fe2d57b9821bcb4e32eb9790a95117044df4314d92ad0995f8967a98218366` | ANM XOR-delta animation (reference interpretation) |
| `O4.ANM` | 4480 | `24b6b3a67b73a5381e80d45d8fd2038e0fe2ed5241f41374607af918ebd44173` | ANM XOR-delta animation (reference interpretation) |
| `O5.ANM` | 6784 | `39d9cfa6c920d686c1a37bea9597a9a70766f6182c359abf055c96ee07000bbf` | ANM XOR-delta animation (reference interpretation) |
| `O6.ANM` | 3328 | `269d6d645a0c5d358224e0f929613af0223535d62fecf76a0c624c5f547b0918` | ANM XOR-delta animation (reference interpretation) |
| `O7.ANM` | 6912 | `7a1b9168d646ff512817a521b0372e1fafc4f05f5c0c43d9e6e7ff66eb3daae0` | ANM XOR-delta animation (reference interpretation) |
| `O8.ANM` | 2176 | `4250e3d86fe547d49ba832a08d292acc51c5e257bfd03ea2ef825d88629c9d52` | ANM XOR-delta animation (reference interpretation) |
| `O9.ANM` | 16128 | `64a91ff1d4733d1dd22a8ea68887ffcf2478fb3d7c7b17a5cdb94b6568487242` | ANM XOR-delta animation (reference interpretation) |
| `PARTY.BLD` | 6207 | `bb11684bed0787b207fd29a0b76a616da3ee80b2270c0ba981de7665765fe9b4` | BLD script / cipher |
| `REPAIR.BLD` | 4983 | `a22f4cab90119911693602fc290e39f4ab6d74cfd6fef765e76739d6ba8efb97` | BLD script / cipher |
| `STARLEAG.ICN` | 27227 | `52030943ce60c927f01cf45f0dfe2b8af805b612ed54c4e499a496d35159349e` | packed nibble graphics / signed RLE |
| `THEATER.BLD` | 1132 | `18aab58a4079eb684af299e12118d3e8256927c7407ea65933b9b1bea096c87b` | BLD script / cipher |
| `TINYLAND.CMP` | 2032 | `59bc6d81218f625670898cb73079f0eb6bf19a2600d1f34f67c990c5c676acc0` | packed nibble graphics / signed RLE |
| `TRAINING.BLD` | 7282 | `a3e8d56ba58319dcdc30be305f2e45dba97fc0d7e3f26f2e4e0a7ec8bb3c0aa9` | BLD script / cipher |
| `VIEWDISK.BLD` | 3544 | `01599372b84c3ebd4d0ca2a6b47e369bfde9b8bedb5dd8f1ffc5ee187093e119` | BLD script / cipher |
| `WEAPON.BLD` | 5850 | `4e08d0fb29c18f0dc0e0f7d403eb0a94aa2f308c7ee9c65fbea3c0436ae4a71d` | BLD script / cipher |
| `WEAPON2.BLD` | 1738 | `4c93942b6fe6909b123701cde0a3b4eb90db3b90b87b0ba9769be3a0908638f0` | BLD script / cipher |
| `WINSCENE.BLD` | 2995 | `d4c54439a1db84867a04430061ae5a448f32c95ac6bcc9cc31eeac9654358a3e` | BLD script / cipher |
| `WWOODBT.SIF` | 4352 | `89f947792eb7c3a9f06e71eb71e19f2bbcb7cedf96a568a94f029b1b7e17fa51` | VERIFIED title music; original `0000:477D..48AE` load / `184B` speaker trace, [M3h evidence](M3D_H_PROGRESS.md) |
