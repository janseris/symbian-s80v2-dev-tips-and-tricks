# Speed on the Nokia 9300: the data cache, what made Maps' 3D view faster, JPEG decoding

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
