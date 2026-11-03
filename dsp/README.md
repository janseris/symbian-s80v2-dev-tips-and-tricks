# The Nokia 9300's DSP (TI OMAP1510, C55x): what's in the ROM

Findings from the ROM files Maps 9300 sent to the PC (1.35-1.48, Tests & log → Send the DSP files;
the code is `DumpBuild` / `DumpNext` in `maps9300/src/mapy.cpp`).
The files themselves are Nokia's and TI's: **never commit them** (`files/` is ignored). The scripts
here are ours.

## The layers (ARM side)

| Layer | Files | What |
|---|---|---|
| Kernel driver | `Ehwa.ldd` (LDD "Hwa"), `Ehwaomap.pdd` ("Hwa.Omap", 106 KB) | `RHwaDevice` / `RHwaTask` (`d32hwa.h`, in the S60 2.1 SDK) |
| TI DSP/BIOS Bridge | `BridgeApi.dll` (35 exports; C++ wrapper classes, returns Symbian errors) | TI's dynamic loader inside (DOF: `.dcd_register`, `.dspbridge_deplibs`, `DLOAD_GetSection`...), mutex `BridgeDcdSync` |
| Bridge config | `Bridgecfg.dll`: `\System\Libs\default.dof55l`, `C5510` | |
| Nokia framework | `BAL.dll`, `GWC.dll` ("gateway component"), `BalBufferManager.dll`, `DeviceManagementServerProxy.dll` (a DSP resource server), `DspMemMapper.dll` | what the DSP plugins use (not BridgeApi directly) |
| A user | `Dspimgc.dll` (ECOM plugin 0x101F85E9, compressed E32Image) | drives `IMGC_TN_NOKIA`: CreateTask / StartTask (BAL), CreateBuffer (BalBufferManager), GetZCMsgPtr (GWC), ReserveDspChunk / MapBuffer / FlushCache / GetDspBufAddr / SendMappedBufferToDsp (DspMemMapper) |

Unrelated despite the name: `Oprbridge.dll` (Opera's), `Bios.dll` (BIO messaging).

## Round 2 (Maps 1.47)

- **The ROM is readable from user code** (tried first in a thread of its own): ROM images can be sent
  whole from memory. 540 ROM images in `Z:\System\Libs`, `\Libs\Plugins`, `\Programs` (1149 files).
- **A table of DLLs** (`iDllRefTable`: u16 flags, u16 count, then entries) holds the used DLLs' **code
  addresses** (header + 0x64) and table addresses, not their headers.
- **The phone's ICL JPEG decoder is ARM-only**: `JpegOptIclDec.dll` (0x101FEA05, used by the ICL plugin
  0x101F9FFF) imports only ESTLIB. The DSP JPEG node isn't used by ICL.
- **The audio codecs come as pairs**: `<Codec>Gwc[TI].dll` (BAL ordinals 2, 9, 20-22;
  BalBufferManager 4; GWC 1, 6, 7, 9-11, 13, 14, 16, 19-21, 24, 26-33) and `<Codec>HwDevice[TI].dll`
  (an MMF hardware-device ECOM plugin: the Gwc DLL, GWC 2, 15, 22, 23, 25). GSM, AMR, AMR-WB, AAC, MP3,
  RealAudio 8, Raw. These small DLLs (3-4 KB) are the clearest example of driving a socket node.
- The framework, all ROM images: `Bal.dll` 0x5090F040, `Balbuffers.dll`, `Balbuffermanager.dll`,
  `Gwc.dll` 0x50911BF0, `Dasfgwc.dll`, `DeviceManagementServerProxy.dll`, `DeviceManagementServer.exe`
  (uid 0x101FAF8D), `RawGwc.dll` / `RawHwDevice.dll` (the RAW_NOK node); sent in round 3 (Maps 1.48).

## The DSP side (`Z:\System\Libs\Plugins`, TI DOF "dynamic object files")

Base image `Dsp_image.dof` (baseimage.out, DSP/BIOS, Apr 2005): nodes `DASFTASK_TI`, `SYNCCLOCK_TI`;
heaps SARAM 0xAE00 words, DARAM 0xE600 words, external 0x80000 words (1 MB); shared memory segment
0x100000..; XDAIS (DSKT2, DMAN, ACPY2), STRM, NODE, MSG.

Dynamic nodes (DCD properties: type 02 = socket node with streams, 01 = message/task node):

| File | Node | UUID | in / out streams |
|---|---|---|---|
| Jpddyn | JPEGDECSOCKET_TI (JPD_TIF_IJPD) | 5D9CB711-4645-11D6-B0DC-00C04F1FC036 | 1 / 0 |
| Jpedyn | JPESOCKET_TI (JPE_TNI_IJPE) | CB70C0C1-4C85-11D6-B105-00C04F329031 | 0 / 1 |
| Imgcdyn (+ _alg) | IMGC_TN_NOKIA (camera image processing: viewfinder, snapshot, sRGB, noise) | 540DCA87-F024-4DEB-8E75-6BE986CE38C3 | 1 / 1 |
| Mp3dyn | MP3DECSOCKET_TI | B11A1F21-4B05-11D6-B0DC-00C04F1FC036 | 1 / 1 |
| Mpeg4aac_dec_dyn | MPEG4AACDECSOCKET_TI | 5C89A1F1-3D83-11D6-B0D7-00C04F1FC036 | 1 / 1 |
| Mpeg4dec_dyn | MP4VD_SOCKET_TI | 7E4B8541-47A1-11D6-B156-00B0D017674B | 1 / 3 |
| Mpeg4enc_dyn | MP4VESOCKET_TI | 98C2E8D8-4644-11D6-8118-00B0D08D729F | 1 / 2 |
| Asddyn / Asedyn | AMR decoder / encoder | 016ACBD1-... / B97B5CF1-... | |
| Wsddyn / Wsedyn | wideband AMR decoder / encoder | 96CED7D2-... / C452FC78-... | |
| Ra8_decoder, ra8lbr_decoder, sipro_decoder, Rv8_decoder | RealAudio / RealVideo (AUDIOSOCKET_RN, VIDEOSOCKET_RN) | | |
| Raw | RAW_NOK (message node, 2 in / 2 out) | 781EB912-5631-11D6-ADBD-000086553665 | |
| Prodtest | PRODTEST_NOK | AE794418-CFD8-4655-AF52-8D42312F27C3 | |

All built 29 Apr 2005 (dd-g02). Measured (Maps 1.33): the phone's ICL JPEG decoder (0x101FF555) runs
on the ARM (no CPU left, ~2x slower than Maps' own), so the DSP JPEG node isn't what ICL uses.

## Formats (as found)

- **ROM images (XIP)** read as files: `TRomImageHeader` (0x64 bytes) then the code at `iCodeAddress`;
  the file read is ~80 bytes short (the end of the export table, the table of DLLs): read them from
  memory instead (1.47).
- **Compressed E32Images** (`EPOC` at 0x10, 0x101F7AFC at 0x1C): header 0x7C bytes, the uncompressed
  size at 0x7C, Symbian's deflate after it: `unz.cpp` with petran's `deflate/*.o` (gnupoc).
- **DOF**: header 36 bytes + verify record 20, the string table, **18** section headers of 28 bytes
  (the target sections), symbols of 12 bytes; data in packets {relocs, size, checksum}. The DCD
  properties are UTF-16BE strings in `.dcd_register` and the section named after the UUID: `dcd.py`.

## Tools

`rom.py` (ROM image header), `armdis.py` (capstone ARM disassembly with literal strings), `dof.py`,
`dcd.py` (every node's properties), `unz.cpp` (decompress an E32Image). Put the files in `files/`.

## What running our own code would take

A C55x compiler (TI's C5500 code generation tools), DSP/BIOS Bridge's DSP-side libraries to build a
dynamic node (DOF), and the ARM-side calls (from the 1.47 round: BAL / GWC / BridgeApi). Using an
existing node (e.g. the JPEG decoder for map tiles, in parallel with the ARM) needs only the ARM side
and the node's message protocol.
