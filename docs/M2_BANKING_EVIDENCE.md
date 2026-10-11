# M2f — ComStar and shop Talk audit, 2026-10-11

## Authority and bounded scope

The supplied unpatched v1.03 executable and original resources are the authority.
This audit uses independently decoded BLD bytes, disassembled unpacked EXE bytes
and whole-script DOSBox runs on the working copy. Both reference directories are
immutable. No reference runtime or substantial GPL implementation is copied or
translated into the independent C engine. Implementation verification is in
progress; research observations alone do not establish a completed milestone.

**VERIFIED:** MAP1 entrance slot 2 has raw words `0C66:C014`, local half position
`(102,20)`, room ID 2, and loads COMSTAR.BLD. Its decrypted payload is 2265 bytes,
SHA-256 `7ce238cd6493269cd13430b4648bee6d955aa2da84ceda670c5d02fd344d0e0a`.
The same audited executable/image hashes as earlier milestones apply.

## ComStar bytecode and transactions

**VERIFIED:** the interface is investment banking. Cash and three C-bill stock
balances are modeled, rather than inventing a generic deposit account. COMSTAR
uses F9 menu 10 (entry choices), 11 (accounts) and 7 (buy/sell, stock selection,
prospectus). Menu 7 is shared: choosing Sell also makes the next stock menu start
on its second company. Its remembered selection is not an independent field per
screen. The entry menu PC is `01B6`, initial retinal-scan wait `02CF`, account
menu `034A`, and change menu `0380`, relative to the decrypted payload.

F5 **06** displays cash and nonzero investments, or the original None response.
F5 **07** buys stock; **08** sells it. The native pauses for stock selection and
numeric input, then returns through `F8 02CD`, `F2`, `FB`. There is one bytecode
wait on the completed transaction, not an additional invented confirmation.

Original code at image `150AA..1569E` (relative segment `14D3`, handler offsets
`037A..096E`) establishes the following. Cash is unsigned 32-bit `D370`, and the
three investment balances are unsigned 32-bit `D374`, `D378`, `D37C`. Buy transfers
`min(requested,cash)` to the chosen balance; Sell transfers
`min(requested,chosen balance)` to cash. Add/subtract uses 32-bit carry/borrow.
Zero moves nothing. Empty cash, no investments and an unowned selected company
each have distinct original responses. The credit and investment totals are
conserved by these transactions, except the original unsigned overflow rules.

The number editor is original image `0E10E..0E315`: initially 0, at most seven
digits, leading zero removal, Backspace erasure, Escape resets to 0 and Enter
submits. Escape does not submit. The shared numeric buffer is overwritten when
the handler formats the later balance display; it cannot establish the earlier
typed amount in a receipt. Recorded keys and inspected frames establish that
amount; the buffer's actual later contents remain separate fixture observations.

**VERIFIED:** unmodified run `work/reference-runs/1791693440826188406`, driven by
[reference-bank.json](../tools/reference-bank.json), has 33 checkpoints. From
35 cash it invests 30 in DefHes (cash 5), sells 7 (cash 12, investment 23), buys
with input 999 (cash 0, investment 35), checks empty-cash, unowned-stock and zero
responses, then sells with input 999 (cash 35, investment 0). The final empty
stock response and outdoor return are captured. Complete decrypted COMSTAR bytes
and original native string bytes are present in the read-only RAM exports.

## Outdoor investments and allowance

The reference notes' description of eight stock records at D390 actually aliases
the NPC records. COMSTAR contains no F5 2A/2B stock initialization. Primary image
`02EE..0449` adds cash and the three real balances with 32-bit wrapping, checks
the pre-update total against the local allowance cap, and updates the balances
on eligible D323 wraps. The functions described as display-only math actually
write back through their far-pointer arguments.

**VERIFIED in the local 50-cap context:** if pre-update total is below the cap,
cash receives 15, without clamping. Each account consumes one RNG draw, even
when empty. Original tables at common DS `02A2` and `02A8` give masks
`255,7,1` and rates `96,90,48`. A nonzero masked draw changes a balance to
`(balance * 100 modulo 2^32) / rate`; zero changes it to
`(balance * rate modulo 2^32) / 110`. Division truncates unsigned. Baker's
growth result above 18000 is shifted right twice. At/above the pre-update cap,
neither the allowance nor these three RNG draws/updates occur. The original
compares the total's high word signed and low word unsigned; extreme overflow
cases are primary-code facts, not claims about a naturally reached cadet state.

**VERIFIED:** [reference-bank-rates.json](../tools/reference-bank-rates.json), run
`1791693786677767965`, adds one C-bill to each other company and waits through
two wraps. Its 29 checkpoints and 460 stable outdoor samples show cash 3 and
balances `[30,1,1]` changing to cash 18 and `[31,0,2]`. Total assets then equal 51;
the next wrap leaves them unchanged. Re-entry displays those balances. The
numeric frame corpus records actual RNG, loop counter and all NPC fields;
native comparisons are still being completed. Full day progression, changing
caps, world economy and campaign timers remain outside this gate.

## Talk in both shops

ARMOR performs F4 `0D 04`, F5 `0C` at `0A97`, then jumps to its main menu.
WEAPON uses room 3 and F5 `0C` at `1604`, then likewise returns. The local
handler is the previously audited original image `09579..097A0`, with activity
text selected by the building's room ID. It supports empty-room response, names
in slot order, Done and local activity/destination replies. No reply RNG draw
occurs in these local rooms. Room 7 recruitment and outer-world replies remain
separate unsupported contexts.

**VERIFIED:** ordinary walks show both empty-shop responses and return. Explicit
controlled preconditions subsequently put slots 1 and 4 in each shop, with stay
timers 5 and 7 and result byte 91. Separate before/after audits record exactly
the eight occupancy pairs and result byte writes in the running working copy;
no executable, resource or save is patched. These are handler checks, not
evidence for natural arrival at those shops. Default gameplay never injects
these contexts.

Runs `1791693440826188386` (Armor, 40 exports including precondition snapshot) and
`1791693440826530230` (Weapons, 60) use the two committed whole-input scripts.
Each occupied handler has 11 checkpoints: menu with two names plus Done, Done
preserving result 91, retained selection, both NPC replies clearing it to zero,
return and exit. Screens establish transient highlights: original menu 20 only
stores its remembered selection on confirmation. NPC equality is required while
indoors; outdoor exit resumes timers in the original and is excluded from the
controlled native checkpoint's disabled-travel projection.

## Text, fixtures and limits

The local BTT2 cache has 43 strings/1448 bytes: the prior 17 NPC strings, 23 bank
literals and three company names. It retains original case, spaces, carriage
returns and bank color control bytes `06 0F`, with source/image hashes and original
addresses in an ignored sidecar. Proprietary text, cache bytes, images and RAM
remain out of Git. Factual fixtures hold numeric state, commands and hashes.

[verify_m2f.py](../tools/verify_m2f.py) reconstructs texts independently from the
original EXE/BLDs and observed numeric values. Native hashes compare a documented
logical concatenation of literals and positioned numeric fields, not screen
pixels or a supposed complete original terminal text buffer. Recorded original
cursor/party, balances, flags, remembered menus and return establish the paths.
Explicit replay idle ticks reproduce observed outdoor counter intervals, without
claiming recovery of individual NPC movement timing between road inputs.

**INFERRED:** generalization to unobserved local transaction paths and campaign
contexts. **APPROXIMATE:** native font/layout, imagery, sprites and pacing.
**UNKNOWN/deferred:** original GAME compatibility, full day/training, other shop
goods/repair/party assignment, world, combat, animation/audio and Windows.
