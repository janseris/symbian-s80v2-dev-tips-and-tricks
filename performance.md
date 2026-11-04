# Speed on the Nokia 9300: the data cache, what made Maps' 3D view faster, JPEG decoding, measuring

From the Maps 9300 notes (moved from `symbian-s80-build-tools/native9300/README.md`, 3 Nov 2026). Paths like `maps9300/` are the sibling repos in the same folder.

## 4b. The data cache (8 KB, 16-byte lines)

Instruction counts miss the memory stalls. Maps 9300's emulator models the cache (`emuvts.py -c`):
read misses per function. What helped (1.13, about -35 % misses per frame, the same frames):
- **Smaller per-element data**: the projected corners 8 bytes instead of 16 (a tile's ~700 fit in the
  cache), the mesh's corners 16-bit.
- **Lay structs out by what is read together**: the fields every pass reads (count, flags, pointer,
  next) in the first 16 bytes, arrays starting on a 16-byte boundary (allocate 15 bytes more and round
  the pointer up), so a triangle's 3 values of an array are one line, not two.
- **Share instead of copying**: polygons pointing at one texture descriptor rather than each a copy.
- **Don't touch it**: a box-against-the-view test per tile (8 corners) skipped ~15-25 % of the
  geometry work outright.
- Writes don't fill the cache (read-allocate), so data written in one pass and read in the next misses
  again.

Measured on a 9300 (Maps 9300 1.23's benchmark, `memprobe.c`: one load per 16-byte line, over 4 KB
and over 128 KB):

| | Time | At 150 MHz |
|---|---|---|
| A load that hits (in an unrolled loop) | 10.3 ns | ~1.5 cycles |
| A load that misses | 275.5 ns | ~41 cycles |
| So one miss costs | ~265 ns | **~40 cycles** |
| 16 bytes read in sequence (`LDM` of 8 words) | 288 ns | ~43 cycles: no gain from reading in order (~55 MB/s) |
| 16 bytes written in sequence (`STM` of 8 words) | 253 ns | ~38 cycles (~63 MB/s, through the write buffer) |

- **A miss costs about as much as 30 instructions.** Maps 9300's 3D frames miss ~40-67 thousand
  times (the emulator's cache model), so ~1.6-2.7 M cycles, about a third of a frame, is waiting for
  memory: worth more than shaving instructions.
- **Sequential reading isn't faster than random reading**: each new line costs a full miss, so a
  copy or a pass over a big array is bound by the ~55 MB/s, whatever the loop does.
- **Trade instructions for misses only at a rate of more than ~30 to one.** A swizzled texture layout
  (2 x 4 texels a line) saved 17-37 % of the texel misses for ~1 instruction a pixel more: about
  break-even, so not done.
- **Pack what is written in one pass and read in the next into as few lines as you can**: those reads
  always miss. Maps 9300 1.24 packed a triangle's record from 5 lines to 3 (x, y as 16-bit pairs) and
  unpacks it onto the stack (which stays cached): 2 misses a triangle less for ~20 instructions more.

## 6. What actually made the 3D view faster

In order of gain, measured in the emulator:

1. **Don't do the work at all.** Skip tiles outside the view before touching them; drop faces
   behind or beside the camera before transforming them; no background fill where the scene
   covers the screen; a polygon budget, submitted near to far so the far ones are what's lost.
2. **Transform shared vertices once (0.92).** A mesh's corner is shared by ~4 triangles.
   Transforming and projecting per triangle did it 3 times per triangle; per vertex per tile is
   ~4x less. Triangles then only look up screen positions. Result: 40–55% fewer instructions
   for the whole frame, the same picture to the pixel.
3. **Sort out triangles in assembly** (back face, off-screen, skipped squares) before building
   any polygon: ~45 instructions a triangle instead of ~140.
4. **The span loop and row loop in assembly** (0.75): ~7 instructions a pixel, 4 pixels a step.
5. **Per-polygon setup in assembly** (the texture gradients, 0.92): ~60 instructions instead of
   ~190. With small triangles (~45 pixels each) the setup costs as much as the pixels.
6. **Fixed point everywhere**, angles as table lookups (`R3D::Sin`), reciprocals from a table.

Maps 9300 1.12–1.13 (the same frames to the bit; a test frame 5.41 M → 4.78 M instructions, ~35 %
fewer cache misses):

7. **An exact box test per tile** (`R3D::BoxVisible`): the 8 corners of the tile's box in camera
   space against the near plane and the 4 sides (a few pixels wider). The old 2D wedge kept ~1/3
   more tiles than the screen shows. Cheapest win of all: 9–23 % of a frame.
8. **The data cache** (section 4b): smaller corners, cache-line-aware struct layout, shared texture
   descriptors.
9. **The bucket loop and a polygon's whole drawing in assembly** (`r3_draw`, `r3_raster_tex`):
   C's per-call glue (struct packing, prologues) cost ~70 instructions a polygon.
10. **Remove tests that can't change the result**: the row loop skipped rows with left > right,
    but then ceil(left) > floor(right) anyway, and the later count < 0 test catches it. Prove it
    before removing it (the clamps keep it true), then check it on the frames.

And outside the frame, **the mesh decoder without floating point** (1.13): a fixed-point transform
built once a submesh (rotation and scale together; the 64-bit sums `(long long) int * int`, one
`SMULL` each), an integer square root for the shading, integer division for the texture
coordinates, shifts for power-of-two cells. On the phone it went from ~168 ms to ~37 ms a tile.
The results differ from the doubles only where a value was within ~1/512 of a rounding edge
(2 corners of 60,000 moved 1/16 m), so it was checked by comparing meshes, not by hashes.

Maps 9300 1.17 (the same frames; 6–14 % fewer instructions):

11. **Chunks inside a mesh without reordering it.** The triangles came in no spatial order (any run
    of 64 spanned the whole tile), and reordering them would change the draw order inside the depth
    buckets (not the same frames). Instead each face gets a grid chunk (a byte); the chunks' boxes
    are culled a frame and the face loop skips a hidden chunk's faces with one table lookup. The
    corners can be reordered freely (only the indices change): by their first face's chunk, the
    corners a set of visible chunks needs are a few runs, which r3_verts takes as they are.
12. **Box against plane with the "p-vertex"** (n·c + |n|·h), unit normals in world space worked out
    once a frame: ~30 multiplies a box, no 64-bit maths. Hierarchical (tile, 4 x 4, 8 x 8), each box
    against only the planes its parent straddles: the plain 64-chunk test cost nearly what it saved.
13. **A wide screen culls a lot at its sides**: in a street-level scene 36–68 % of the projected
    triangles were wholly off one side.
14. **Special cases without flag tests**: a clamp-free row loop for triangles wholly inside, chosen
    with three unsigned compares (`cmp; cmpls; cmpls; bhi`: below 0 counts as huge); loop copies
    with GAS `.macro` / `.if` instead of a test each time round. Prove the clamp can go: the rows'
    ends stay within 1/8 px of the corners (floor rounding of 16.16 steps, under 8192 rows).

The panorama (Maps 9300 1.16) shares the renderer, so 3–6 and 8–10 were already its own. Of the
rest only 7 carried over: its sphere's pieces were picked by a cone around the view, which on a
640 x 200 screen is round and ~3x too tall; testing the pieces' corners against the 4 sides
(each corner once, cached a frame) halved the pieces (87 → 41) for the same frame. A rule that
follows: **a round test on a wide screen wastes half its area; test the real sides.** After
that ~80 % of the frame is the 4-pixel span loop, which only packing u and v in one register
(one add instead of two a pixel, ~11 % of the frame, but 16-bit halves: not the same pixels)
would still shorten.

## 6a. Maps 9300 1.59: front to back, and the geometry's cache misses

A real LoD 21 frame (Prague, street level, 8,000 triangles, 320 x 200) went from 193 to 149 ms on the
phone, 30 m up from 176 to 138 ms. Each step was tried in the ARM emulator first, on the phone's own
dumped frame (`emuvts.py`, see 6c), then measured on the phone.

**What the phone showed that the emulator didn't:**
- **With small triangles the drawing follows the triangle count, not the pixels.** Front to back
  cut the pixels drawn from 76 k to 27 k (30 m up) and saved ~1 ms: each triangle cost ~10 us
  (~1,500 cycles) whatever its size (the median was 4.5 px). The work per triangle is what to cut
  (and a triangle budget is a view distance).
- **Hidden triangles are most of them.** Drawn nearest first, 5,500 of the 8,000 turned out wholly
  hidden. Rejecting those early is where front to back paid (184 → 162 ms with the steps below).

**Front to back, step by step (all the same pixels as each other, ~5 % different from painter's
order: shared edges, and the order within a 1 m depth bucket):**
1. **A bit a pixel** (40 bytes a 320 px row, 8 kB a frame) instead of span lists: a row within one
   32-pixel word is a mask, a load, an AND and a compare. Rows' ends (16.16) are clipped in place to
   the first run not drawn yet; more runs: the same rows drawn again in more passes, so the tuned
   row loop stays untouched.
2. **The usual cases in assembly, the rest in C**: one word all new / all drawn, two words, a partly
   drawn word whose free part is one run (its ends by a **de Bruijn multiply and a 32-byte table**:
   the ARM9 (ARMv4T) has no `CLZ`). Only rows with several gaps go to C (a few hundred a frame).
3. **Reject before any setup**: first a triangle's **bounding box** against the bits (catches 9 of 10
   hidden ones, no rows' ends computed), then the exact rows before the texture gradients.
4. **Read the record only as far as needed**: the hidden test straight from the packed record in the
   drawing loop, not unpacked, and the record laid out so that test needs only its first 16 bytes
   (n, next, the 3 corners' x | y).
5. A big triangle that the reciprocal table can't take got a C helper with a division instead of the
   whole slow path, so it stays in the fast path (and is covered like the others).

**The geometry (−18 % cache misses, the same frames):**
- **Sort faces by chunk when the mesh loads** (a stable counting sort of indices, uv, shade): a chunk
  off the screen is then skipped as a range, its faces never read (they were ~30 % of a frame's).
  1.17 had kept the file's face order to keep the frames identical; with front to back that no
  longer mattered.
- **Don't write a list in one pass and read it in the next.** The cache doesn't fill on writes, so the
  kept-triangle list, and the indices and corners it pointed back to, all missed again. Building each
  kept triangle's record at once in the same loop (its corners still cached) saved 12.7 k misses of 98 k.
- **On-screen first**: the corner transform's clamp and screen-side tests only in a branch for
  corners off the screen (−12 % of its instructions, the same results).

**Tried and not worth it (measured, so not repeated):**
- **Corners renumbered in first-use order**: no change; the meshes already came that way.
- **Half-size textures for far tiles**: −1.3 % misses at best; after front to back textures were only
  ~10 % of the misses, and at 8,000 triangles nothing is far.
- **Skipping groups of back faces per chunk** (normal cones): an exact offline count (Python over the
  dump) gave an upper bound of ~2 ms for a complex change and ~150 kB of RAM.
- **The DSP drawing the frame**: as fast as the ARM (textures in the shared SDRAM: `dsp/README.md`).

**Outside the triangles (the frame's "rest"):**
- **Copy only what changed to the screen**: a 320 px game view in a 640 px window copied the whole
  window and refilled its sides every frame.
- **`User::Available()` walks the heap's free cells**: not something to call every frame with 20 MB
  of tiles in the heap; RAM changes slowly (every 250 ms is plenty).
- **`TInt64` multiplies are library calls** (no 64-bit multiply instruction in use): a view test
  doing 8 per tile per frame went to 32 bits with a range check (within 2.5 km nothing overflows).
- **Free a view's caches when it closes**: 20 MB of 3D tiles held after leaving the 3D view left the
  phone ~100 kB free and the network code failing.

## 6c. Measuring on the phone

- **The tick is 15.6 ms**: per-frame timings from `TTime` are whole ticks. Time 32 frames together
  (one key) and divide; repeat each figure twice, and switch the change on and off with a key in the
  same run (A/B, the same scene) instead of comparing installs.
- **Measure the path the frames really take.** A `DrawNow()` loop went through the window server and
  copied the whole view each time, while the app's frames went straight into the screen memory:
  a different "rest".
- **Replay a real frame on the PC**: dump the frame's input (meshes as in RAM, camera, textures),
  run the phone's own ARM code on it in an emulator (Unicorn) with a cache model: instruction and
  miss counts per function and per data, and a frame hash to prove a change draws the same pixels.
  It matched the phone's counts exactly; installing and loading a city takes ~10 minutes, a replay
  seconds.
- **Count before building**: an upper bound from a quick offline script (how many faces a test could
  ever skip, how many misses a smaller texture could save) ruled out several ideas in minutes.
- **GCC 2.9 / ARMv4 bits that bit here**: a struct assignment can become a `memcpy` call (copy the few
  fields by hand in C that has no library); `MUL rd, rm, rs` needs rd ≠ rm; no `CLZ`.

## 6b. JPEG decoding (the 3D photos, the panorama)

- **Decode at the size you need**: a half-size IDCT (4x4 from the lowest frequencies of each 8x8
  block) instead of decoding fully and halving: 45 % of the instructions (1.11).
- **IDCTs and colour conversion in assembly**, with the C kept as the reference (1.12).
- **Huffman decoding of the usual block in assembly** (`jpeg_block`, 1.13): DC, AC, end of block,
  stuffed `FF 00` bytes, all from 9-bit lookup tables; anything else (a longer code, a marker, the
  end of the data) returns "not done" **before changing any state**, and the C decodes that block
  from the start. Fast paths that can bail out to the full C code are simple to get right.
- **Combined tables**: the AC table gives the run, the value bits and the code length in one
  lookup when they fit 9 bits (most do); the zigzag table carries the row bit (`z | 1 << (8 + row)`)
  so tracking non-zero rows is one `ORR`.
- **Move table bases, not indices**: per pixel pair, add the chroma terms to the three
  table pointers once (`r565 + crR`, ...), then each pixel is `ldr [base, y, lsl #2]` x 3:
  30 instructions a pair instead of 34.
