# Lua 5.4.9

Unmodified C sources and headers from the official release:
https://www.lua.org/ftp/lua-5.4.9.tar.gz

Archive SHA-256: `2335b6c582a52654f94612bf10d2f4672805d05329aa6568b1d8cd9e5c6fb8e6`.
Downloaded and verified 2026-10-17 against https://www.lua.org/ftp/.

MIT license; see LICENSE.txt and the notices retained in the source. The parent
project's GPL-3.0-only license does not replace Lua's license.

Only the interpreter/compiler core and auxiliary C API are built. No standard
libraries are opened by BtechPort. Programs have access only to the small
`game` query/continuation API, with a 256 KiB allocator limit and 10,000 VM
instruction limit per event. Lua VM stacks are never serialized.
