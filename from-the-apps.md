# Tips found by the other native 9300 apps

From the Maps 9300 notes (moved from `symbian-s80-build-tools/native9300/README.md`, 3 Nov 2026). Paths like `maps9300/` are the sibling repos in the same folder.

## 9. From the other native apps

Found in MP4 Player 9300 (`mp4player9300/README.md`), Browser 9300 (`webbrowser9300/browser9300/README.md`),
Instagram 9300 (`instagram9300/README.md`), Net Helper 9300 (`nethelper9300/README.md`) and GnuBox
(`gnubox-s80/notes/`); the version that found it in brackets.

**Speed**
- **Build with `-O2`** (`OPTION GCC -O2` in the `.mmp`): the SDK's default is `-O`; MP4 Player's
  decoding went 19 % faster (MP4 1.2/1.4).
- **The emulator's instructions on the phone:** ~14-20 ns each (2.1-2.9 cycles at 150 MHz) for decoding
  that mostly hits the cache (MP4 1.7: 2.04 M instructions = 28.9 ms; 1.11: ~19 ns). Much more than
  that means memory traffic (MP4 1.20).
- **GCC 2.9's `short`s:** no 16-bit loads or stores in its output (each access becomes byte
  operations); use `int` for working arrays (MP4's coefficient blocks and IDCT, 1.7). Constant
  multiplies become shift / add chains; big loops spill registers.
- **Tables that fit the 8 KB data cache:** MP4's colour conversion tables went from ~11 KB to ~3.5 KB,
  two rows per chroma row, two pixels per 32-bit store (1.3); then in assembly with byte tables
  indexed by Y + chroma: 42.3 to 12.7 instructions a pixel (1.7).
- **`memcpy` / `memset` / `strlen` in assembly** (`lib/fastmem/`, from Browser 0.6): 4 KB memcpy 527
  instructions against 20,484 for GCC's loop; a quadratic copy (an array copied on every start tag)
  was 81 % of a page's work: look for those first.
- **The timers:** `User::FastCounter` runs at 64 Hz on the 9300, the same as the tick: average over
  many frames (MP4 1.2).
- **Writing files:** in 32 KB pieces, not per 2 KB network record (Instagram 0.19: a flash write
  each was the slowness).
- **Start fast:** open `RSocketServ` sessions on the first request, not at start (the first may start
  ESOCK); read settings files when first needed (Browser 0.26).

**Drawing**
- **Straight into the screen memory** (direct screen access; MP4 1.14-1.17): find the layout with a
  self-test (draw 16 pixels with the screen's graphics context, look for them in the memory: the
  offset and line length; write 8 and read them back), every run (a saved "passed" skipped it once:
  NULL screen address, KERN-EXEC 3, 1.15). Start the picture at an even x (word-aligned lines, or
  the slow path runs); the window's screen position is window coordinates + the window's position
  (the normal window starts at x = 92). When the window server reports the area covered (a menu),
  draw the old way. Saved ~7-9 ms a frame of the window server's copy.
- **`BitBltMasked` copies the source where the mask is black** unless `aInvertMask` (Instagram 0.43,
  Browser 0.24: icons and AIF masks the other way round showed white boxes).
- **BITGDI 3 = no font selected:** a `DrawText` after another part of the code discarded the font
  (Instagram 0.57). Also from a masked blit asking for more than the bitmap has (16x16 of a 16x15
  picture, 0.41).
- **Draw from a callback, not inside network callbacks:** the main thread has ~8 KB of stack; a page
  drawn deep in the HTTP client's callbacks overflowed it (KERN-EXEC 3, Browser 0.15). Measure frames
  from `sub sp` in the ARM objects; let `Render()` only ask, and draw from an idle callback.
- **Don't give `.ico` files to the phone's ICO decoder:** PNG-in-ICO favicons crash it (KERN-EXEC 3,
  Browser 0.17); decode them yourself.

**Panics worth knowing**
- **USER 23 / USER 11:** an 8-bit / 16-bit descriptor over its maximum length. A `TPtr8` taken before
  its buffer was flushed keeps the old length (Browser 0.25, Instagram 0.60); a `TBuf<80>` status line
  that got 84 characters (Instagram 0.58). Size buffers for the worst escaping (`&` to 5 bytes, UTF-8
  up to 3).
- **E32USER-CBase 40** in the Java comms when Java read Bluetooth while downloading (Net Helper 0.4):
  do Bluetooth in a native thread.
- **Killing a thread in the middle of socket / TLS calls** was followed by the phone restarting (Net
  Helper 0.3): let it close its own connections and finish.

**Memory**
- `EPOCHEAPSIZE` in the `.mmp` (up to 32 MB used); size caches from the free RAM (`HAL`,
  `UserHal::MemoryInfo`) and keep a reserve (2.5-3 MB); compress the heap after dropping things so the
  phone gets the RAM back (Browser 0.12, Instagram 0.31).
- A decoder with its own chunk heap (`User::SwitchHeap` around its calls; MP4 Player, up to 12 MB).
- No writable static data: tables `static const` without pointers; lookup tables built at run time
  in an object (MP4's VLC tables).
- CPU load without the kernel's CPU times: a lowest-priority thread counts how far it gets in 0.1 s
  once a second; less than its best = busy (Browser 0.13).

**Network**
- **Speeds measured:** USB IP passthrough: plain HTTP ~222 KB/s, TLS ~121 KB/s (Instagram 0.25; the
  phone's RNDIS + TCP, not the cable); GnuBox measured ~107 kB/s through it. Bluetooth via GnuBox
  ~20-30 kB/s (the 8 KB default TCP window per connection).
- **Bluetooth:** error -6031 reaching another phone usually means a Bluetooth link to a PC (PC Suite)
  is up and blocks it (Net Helper 0.5).
- **Java on the 9300** can't keep connections open or open sockets to 80/443 unsigned, but may call
  `http://127.0.0.1`: a native helper can do its network work (Net Helper).
- **Installing:** `FR,RI` in the `.pkg` starts the app after installing; the installer's own prompts
  stay (Series 80 has no silent install API; Instagram's auto-update).
- The SDK's zlib (1.1.3) inflates gzip after skipping its header (raw inflate; Instagram 9300).
