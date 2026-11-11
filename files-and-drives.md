# Files and drives: where to save, what the drives are

From Browser 9300 0.62-0.65 (11 Nov 2026), on a Nokia 9300. What is measured on the phone and
what is only the SDK's word is marked.

## The drives

| Drive | What | Size (this phone) |
|---|---|---|
| C: | The phone's flash (128 MB NAND, 80 MB for the user). File manager: "Communicator". | 79.8 MB |
| D: | **The memory card** (MMC). File manager: "Memory card". | 122.1 MB (a 128 MB card) |
| E: | Not in Nokia's documentation, and the File manager can't open it ("Show system folder" in its settings shows only `C:\System`). The browser could write ~25 MB to it before "disk full" (-26), and a list that left out only RAM and ROM drives left it out, so it is most likely a RAM drive. Whether a restart empties it, and what made it, isn't checked. | 25.9 MB |
| Z: | ROM: the system, read only. | |

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
  on the drive, else `KErrInUse`). Not run on the phone yet; don't offer it for C: or Z:.
