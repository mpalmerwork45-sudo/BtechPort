# M2e — two MAP1 shops, 2026-10-11

The user expanded the next gate to two shops. The bounded implementation target
is the Armor Shop's flak vest and Weapons Shop's knife, ordinary map entry,
confirmation, equipment/credit changes, and return to exploration. Other goods,
repair, shop Talk and multi-member assignment remain outside this gate.

## Primary observations

**VERIFIED:** unmodified original run
`work/reference-runs/1791690976267363973`, driven by
`tools/reference-shops.json`, bought both items without controlled memory writes.
Inputs, screenshots, full guest RAM and read-only projections remain in ignored
`work/`. The initial state has 35 credits, allowance cap 50, three zero investment
accounts, one active party member, weapon/armor/protection all zero.

| Original checkpoint | Credits | Weapon C61F | Armor C621 | Protection C622 |
|---|---:|---:|---:|---:|
| start | 35 | 0 | 0 | 0 |
| armor-item, before Yes | 50 | 0 | 0 | 0 |
| armor-buy | 0 | 0 | 1 | 25 |
| weapon-item, before Yes | 15 | 0 | 1 | 25 |
| weapon-buy / exit | 13 | 1 | 1 | 25 |

The last weapon snapshot is outdoors at half-coordinate (32,44). The armor
snapshot is outdoors at (50,124). The final entrance step is deferred until exit;
the indoor player position remains the approach square. D316 (story index 10)
becomes one when entering the Armor Shop too: it is not exclusively a Citadel
flag. D317 (index 11) is the native purchase-success byte.

MAP1 header waypoints/room map place Weapons Shop in slot 3 at raw
`0C20:C02C`, Armor Shop in slot 4 at `0C32:C07C`. These are loaded from MAP1,
not substituted coordinates. Actual BLD payloads, excluding their size words:

| Resource | Size | Decrypted SHA-256 |
|---|---:|---|
| ARMOR.BLD | 3386 | b02d6e830f444d383c51b49013c6749d12cf4d9742a561c34896745a39de86f3 |
| WEAPON.BLD | 5848 | 4bbc0075e95889a5452c057fd8b6190c363573afced3394a85f2d24cdf67961e |

## Instruction and bytecode evidence

The audited EXE/unpacked image identity is recorded in `M2_TALK_EVIDENCE.md`.
Primary disassembly can be reproduced with `objdump -D -b binary -m i8086
-M intel` on ignored `work/unpacked-image.bin`. Reference assembly files were
used to locate routines, then checked against those executable bytes.

* Image `156F7..15778` (original `1CD3:09C7`) selects armor through UI menu
  fields 0178/0168, clears D317, compares/subtracts an unsigned 32-bit price
  from D370, sets D317, and dispatches equipment assignment. Common DS 4F26
  at four-byte stride gives the flak vest's selection-1 price 50; 4DDB at
  byte stride gives its protection 25.
* Image `1577B..15817` (original `1CD3:0A4B`) selects blades through UI 0198,
  accounts for other weapon categories, subtracts one for the price index,
  and performs the same comparison/subtraction/result update. Common DS
  4F44 gives knife price 2. This is F5 operand 0B, not operand 05.
* Image `919E..93A5` and `93A6..9578` (original `0FDC:13DE` / `15E6`)
  count active party slots using C614 at stride 17. With one active member
  they directly write C621/C622 and C61F respectively; no assignment menu
  is shown. Other fields in the captured equipment region stay unchanged.
* VM `0FDC:02BD` invokes Yes/No for F6 and follows its two-byte target on
  Yes, otherwise skips that word. `0FDC:0367` sets two signed text-position
  bytes for F0. F5 operand 0A formats/displays credits without clearing
  the existing BLD text. Shop menu selectors are independent remembered
  fields at UI `0098 + 16 * menu_id`, verified before and after both buys.
* Armor F9 IDs 12/13/14 have 4/6/5 choices; weapon IDs 30/15/16 have
  3/4/7. Armor enters menu 13 in this trace because D316 is already one.
  The scripts' F7 index 39 tests D333; the baseline value is zero.
* Armor flak-vest description starts 02C2, confirmation 093F, F6 Yes
  target 0961, F5 09 success target 0C5A. Weapons knife starts 03AF,
  confirmation 1391, F6 Yes target 13AA, F5 0B success target 14C8.
  Both success texts end with F2/FB and jump to their original main menu.

## Allowance needed by the loop

**VERIFIED in this context:** original main-loop image `02EE..03D9` tests the
pre-update cash plus three investment balances against the allowance cap when
D323 wraps. With local D310 zero and cap greater than assets it adds 15 cash
and consumes three account RNG draws. It tests the pre-update assets; this is
not a cash clamp. The original run goes 35→50 before armor, then 0→15 before
weapons. Investments at D374/D378/D37C are not inventory, contrary to provisional
shop notes in the reference checkout.

The port extends M2d's single pending-allowance schedule to this zero-account,
50-cap context so purchases can fund subsequent allowances. Native frame pacing
remains **APPROXIMATE**. General investments, cap progression, invasion/day
countdowns and global RNG integration remain **UNKNOWN/deferred**. Replay waits
are explicit; different wall-clock durations are not behavioral evidence.

## Completed implementation and checks

Independent C VM/core changes load both authentic scripts, implement their
variable-sized remembered menus, F6 confirmations, F0 positions and F5 09/0A/0B
services for the two verified goods. Native text displays the captured decimal
cash at its actual position in the concatenated output. Rendering keeps the cash
line separate from the item menu. Unsupported goods, repair and nonlocal Talk
stop with diagnostics. Recovery restores pre-choice cash/equipment and story.

**VERIFIED:** 56 checkpoints from the purchase run above and 65 from unmodified
boundary run `work/reference-runs/1791691394449093827` pass. The latter is driven
by `tools/reference-shop-boundaries.json`; it declines both goods and attempts
another flak vest at zero credits. Armor refusal clears D317, preserves the
equipped vest/cash and ends the building after its response. Weapon No returns
to the category menu. Both retain their independent item highlights. The second
run's longer final wait receives another allowance: final credits are 28 rather
than the first run's 13. Neither run changes guest memory/resources.

Fixtures contain only numeric observations, action/wait sequences, resource
offsets and hashes. The verifier checks original input provenance, full BLDs in
guest RAM, cursor and party, zero investments/one-member preconditions and exact
equipment-region differences (only C621/C622 for armor, only C61F for weapons).
Native replay waits are derived from successive captured D323 decrements; the
loop counter matches each checkpoint. They do not recover the precise placement
of original NPC frames between individual road keys or wall-clock timing.

Both complete native routes test BTP6 restoration and identical continuation at
all **6137 ticks**. The shop suite has **30928 assertions**, including malformed
VM/state, confirmation, 49/50 and 1/2-credit boundaries, no debit on No,
unsupported-item rollback/recovery, native-service budgets, cap overshoot and
BTP5 migration. Four CTest suites, prior 420 core/94 script/1741 NPC assertions,
four Python checks and all earlier differential routes pass.

Private-X11 SDL runs all 3064 purchase-route/tail ticks through native events,
closes automatically, and matches the complete final headless replay state.
Headless ASan/UBSan/LeakSanitizer pass both shop routes and previous milestones;
SDL/backend remains outside sanitizer coverage. Menu/confirmation frames were
inspected for readable original mixed-case text. Layout, glyphs, sprites and
cadence remain **APPROXIMATE**; wider economy/party/shop/campaign parity is not
claimed. Proprietary BLD/EXE/text/RAM/graphics remain locally loaded and ignored.
