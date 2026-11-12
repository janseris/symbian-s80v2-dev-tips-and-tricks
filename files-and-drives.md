# Files and drives: where to save, what the drives are

From Browser 9300 0.62-0.68 and Maps 9300 0.12-1.60 (its tile caches; Oct-Nov 2026), on a Nokia 9300.
What is measured on the phone and what is only the SDK's word is marked.

## The drives

| Drive | What (`RFs::Drive`: media type; drive / media attributes) | Size (this phone) |
|---|---|---|
| C: | The phone's flash (128 MB NAND, 80 MB for the user). File manager: "Communicator". `EMediaFlash`; local, internal; formattable. | 81 742 KB |
| D: | **The memory card** (MMC). File manager: "Memory card". `EMediaHardDisk`; local, **removable**; formattable, lockable. | 125 050 KB (a 128 MB card) |
| E: | **A RAM drive.** Not in Nokia's documentation; the File manager can't open it ("Show system folder" in its settings shows only `C:\System`). `EMediaRam`; local, internal; **variable size**, formattable. Its free space is the phone's free RAM, and every byte stored on it is RAM taken from all apps. | grows with what is on it |
| F:, G: | Listed, `EMediaNotPresent`, `Volume()` -18 (KErrNotReady). | |
| Z: | ROM (`EMediaRom`; rom, internal; write protected), name "RomDrive", size 0. | |

**RAM** (HAL, the same phone; more in [memory.md](memory.md)): `EMemoryRAM` 47 104 KB, `EMemoryROM` 18 432 KB, page 4096 B. So of
the 64 MB SDRAM chip, 18 MB holds the ROM: the system code lives in NAND, which can't run code,
so it is copied into RAM at start-up. That leaves 46-47 MB, of which the system's servers take
~21 MB: **~25 MB free at most for apps**, matching what the apps measured (and TaskSpy's "46 MB,
~20 MB free at boot" in reviews).

Measured with Browser 9300's "Drives and RAM test" (0.67, `about:drivetest?write`: 2 MB written,
read and deleted; the free RAM and the drive's free space before and after):

| | Write 2 MB | Read 2 MB | Took |
|---|---|---|---|
| D: (MMC) | 4515 ms (~450 KB/s) | 2520 ms (~810 KB/s) | the card's space, no RAM |
| E: (RAM) | ~8.7 MB/s (1600 KB in 180 ms, then full) | ~15 MB/s | RAM, byte for byte |

- **A file left on E: eats the RAM of every app.** Browser 9300 before 0.63 saved "to the memory
  card" on E:; a failed 24 MB download stayed there, and the phone had **1.6 MB of free RAM** left
  (the RAM drive "size" 25 187 KB = 23.5 MB stored + the 1.6 MB free). Never write to E: unless
  you delete it again, and never offer it as a place to save.
- **E:'s size isn't fixed**: Maps 9300 0.98 saw it as ~14 MB, Browser 9300 as 25 MB with a file on it:
  it is whatever is stored plus the free RAM, so it changes with every allocation.
- **E: as a cache:** it is ~10x faster to write and ~20x faster to read than the MMC and survives
  the app's exit (not a power-off), but it costs the same RAM as keeping the data in the app.
  Worth it only for data several apps or several runs reuse; not for textures one app loads into
  its own memory anyway.

- **Never pick the memory card by its letter.** Browser 9300 used E: as "the memory card" up to 0.62.
  On this phone that is the 26 MB extra drive, so downloads "to the card" filled it and failed at
  25 MB with -26. **Find the card with `RFs::Drive()`: the drive with `KDriveAttRemovable` in
  `iDriveAtt`** and a medium in it (`iType` not `EMediaNotPresent` / `EMediaUnknown`). Leave out
  `EMediaRam` and `EMediaRom` drives and media with `KMediaAttWriteProtected`.
- **`RFs::Volume()` is right.** `iSize` and `iFree` (`TInt64`) gave the same numbers as the File
  manager (C: 81742 KB capacity, 19330 KB free; D: 125050 KB, 102704 KB free). If the free space
  looks wrong, check which drive it is first.
- `fs.DriveList()` + `fs.Drive()` + `fs.Volume()` for every drive is a quick way to see what a phone
  has; log the type and attributes.

## Where to save

- **User files (downloads, exports, documents): the user's folder.** On Series 80 it's
  `CknEnv::GetDefaultPath(TDes&)` (`cknenv.h`, **`ckncore.lib`**). The SDK says: *"Returns the
  default path "c:\MyDocs\" or the equivalent on the device (`R_CKN_USERS_ROOT_FOLDER_PATH`). This
  is a default path that most applications use, for example, the initial directory that the File
  Manager application goes to."* The built-in browser's save dialog starts there, and the File
  manager shows it as Communicator / "My files" ("Moje soubory" on a Czech phone). The name on
  disk may differ from the name shown, so ask the API rather than hard-coding `C:\My files\`.
  (Browser 9300 0.65 uses it, falling back to `C:\My files\`, then `C:\Documents\`; the path the
  phone returns isn't logged yet.)
- **The app's own settings and data: `C:\System\Data\<app>\`** (or `C:\System\Apps\<app>\`). This
  is the pre-Symbian 9 convention: `\System\Apps` holds installed apps, `\System\Data` settings and
  data (Z:'s copy holds the defaults), and `Documents` / "My files" the user's files, never apps.
  (Symbian 9 replaced this with `\sys\`, `\private\<SID>\` and `\resource\`, "data caging"; that
  isn't on S80.)
- **Don't put user-visible files in `\System\`.** Browser 9300 used `C:\System\Temp\` for
  downloaded installers from 0.1 to 0.63, its own choice with no convention behind it. Files there
  are not shown in the File manager unless "Show system folder" is turned on in its settings, and
  they use phone memory without the user knowing. A `.sis` can be installed from any folder (`RApaLsSession::StartDocument`).
- **Keep out of other apps' and the system's files.** A tool that counts or lists files should not
  enter `\System\` at all. `CDirScan` walks into every folder, so walk with `RFs::GetDir()` and a
  queue of folders instead, and skip `System` at the root. Only delete files your app created:
  keep a list of their paths.

## Many small files (a cache)

Maps 9300 keeps map tiles (10-40 KB each) and 3D files (~30 KB) as one file each, thousands of them.
Its log gives the averages of real use (the reads and saves in a download thread, while the app draws):

| | Read a file | Save a file |
|---|---|---|
| C: (the phone's flash) | 190-640 ms | **1.8-3.6 s** (25-30 KB tiles) |
| D: (MMC) | 80-140 ms (~390 KB/s for the 3D files) | 370-520 ms |

- **Put a cache on the card.** C: is the slowest place to write on this phone: a save took ~5x as
  long as on the card, and reads were 2-4x slower too. Measure with your own app before deciding:
  the card's numbers also depend on the card.
- **No folder of hundreds of files.** Saving into a folder of ~600 files on C: took ~1.5 s each
  (0.12): every create and open searches the folder. Spread the files over subfolders by a hash of
  the name (Maps uses 32: `tiles2\00` .. `1f`).
- **Don't ask the disk for a file that isn't there.** A miss costs an open that searches a folder
  (two, if you try two names). Keep an index in RAM: Maps keeps one bit per name hash (8192 words,
  32 KB) filled from the folders' listings at the start (`RFs::GetDir` with `ESortNone`) and set on
  every save; a clear bit means "surely not on the disk" and goes straight to the network.
- **Write a file with one `RFile::Write`**, not in pieces (each write to flash is slow), and don't
  write files while the app needs the CPU or the link: Maps saves only when no download waits and
  2 s after the last one was asked (a 4 s save on the card kept the phone from reading the
  Bluetooth link: its TCP window filled and tiles took 1.5-3.6 s). Queue the saves, and when the
  queue is full, save the oldest at once rather than dropping it (dropped files are downloaded again
  next time).
- **Least recently used without rewriting files:** an LRU cache needs the last use; `RFs::SetModified`
  on every hit is a write. Maps updates a file's date at most once a day.
- **Keep room on the drive.** Maps keeps a cache within the drive's free space less a margin (8 MB
  on C:, where the system and other apps need room; 2 MB on a card), not a fixed size: a fixed 48 MB
  on a 128 MB card filled it, and a rule "20 MB free at each start" moved a card filled by the cache
  itself back to C:.
- **Deleting is cheaper than writing** (Maps' guess for its estimates: ~40 ms a file), but a few
  thousand files still take minutes: do it as a blocking operation with progress, or bit by bit
  while idle (Maps cleared its old cache folder a few files at a time between downloads).
- **`RFs` is per thread.** A download thread needs its own `RFs::Connect()` (or a session shared
  with `RFs::Share()`); Maps' threads each have one and take turns on the cache with an
  `RCriticalSection`.

## Downloads and partial files

- **Delete the part when a download fails or is stopped.** A file opened with `RFile::Replace` and
  written in pieces stays at the size written when the write fails (e.g. -26, disk full). Nobody
  lists it, and it keeps its space. Browser 9300 left a 25 MB part of every failed attempt
  until 0.62.
- **Check the free space before a big download** (`RFs::Volume` on the target drive, against the
  `Content-Length` plus some margin) and say so before starting.
- **Lost clusters:** a file not closed (the app or the phone stopped while writing) can leave
  clusters marked used that no file owns. The file system counts them as used; a tool that adds up
  file sizes counts them as free. `RFs::CheckDisk(_L("D:\\"))` reports it and
  `RFs::ScanDrive(_L("D:\\"))` frees them (both in `efsrv.lib`; `ScanDrive` needs no files open
  on the drive, else `KErrInUse`). `CheckDisk` only reads: on this phone it returned 0 (no
  errors) for C: in 225 ms and for the 128 MB card in 210 ms, with the browser running (Browser
  9300 0.68, "Check the phone and the card"). `ScanDrive` changes the drive: not tried, and don't
  offer it for C:, Z: or a RAM drive.
