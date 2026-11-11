# RAM: how much there is, where it goes, how to measure an app's share

Measured on a Nokia 9300 with Browser 9300 0.66-0.71 (11-12 Nov 2026). The drives (the RAM drive
E: among them) are in [files-and-drives.md](files-and-drives.md).

## The numbers

| | KB | Source |
|---|---|---|
| SDRAM chip | 65 536 | Nokia's specs |
| `HAL::Get(HALData::EMemoryRAM)` | 47 104 | the RAM the OS manages |
| `HAL::Get(HALData::EMemoryROM)` | 18 432 | the ROM image (Z:), copied from NAND into RAM at boot: NAND can't run code in place, and Symbian 7.0s has no demand paging |
| `EMemoryPageSize` | 4 (4 096 bytes) | the memory page |
| Free when an app starts, nothing else open (`EMemoryRAMFree`) | **25 140 - 27 164** | Browser 9300's log, three starts |
| The system's servers and the rest | ~20 000 | 47 104 less the free RAM |

- **~25 MB is the most an app can have.** 64 MB = 18 MB ROM copy + ~21 MB system + ~25 MB
  free. Reviews say the same ("TaskSpy shows 46 MB, ~20 MB free at boot").
- **Anything on the RAM drive E: comes out of that.** With a 23.5 MB file left on E:, the phone
  had 1 636 KB free (and every app ran short); after deleting it, 27 164 KB.
- **Print RAM in kilobytes with K**, as the old games and apps do: "RAM free 26112K of 47104K".

## An app's own RAM

- `User::AllocSize(n)`: the bytes allocated in the heap now (what the program holds).
- `User::Heap().Size()`: the heap chunk's size (what the heap took from the system, at least the
  allocations).
- **The app's chunks:** `TFindChunk` with `RProcess().FullName()` + `"::*"`, `RChunk::Size()` for
  each. On the 9300 an app's process has only one named chunk, its stack:
  `Browser 9300[0f5a9310]0002::Browser 9300::$STK`, 296 KB (the main thread's and the other
  threads' stacks). The heap is not among them, so add `User::Heap().Size()`.
- **Bitmaps live in the font and bitmap server, not the app:** a `CFbsBitmap`'s pixels
  (`ScanLineLength(width, mode) * height`) count against free RAM but not against the app's
  heap. Browser 9300's off-screen page bitmap, 640 x 200 in EColor64K, is 250 KB.
- Browser 9300 at the start page: the stack 296 KB + the screen bitmap 250 KB + the heap.

## What takes RAM in practice (Browser 9300)

- **JavaScript:** a page's engine (MuJS) with Blazor's 200 KB `blazor.web.js`: a heap peak of
  **5.5 MB**, and ~4 s of the 150 MHz CPU to compile and run it. A page without big scripts: a
  few hundred KB.
- **CSS:** Bootstrap 5's minified CSS is ~750 rules; a 9 KB page styled with it takes ~300 ms.
- Leave ~0.5 MB free for the system (the browser's caches and pictures stop at 512 KB free;
  pictures keep 3 MB free before they give way).
