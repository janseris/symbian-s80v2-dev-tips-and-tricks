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

## Round 3 (Maps 1.48): the framework

25 ROM images, sent whole from memory. The DLL graph (from their tables of DLLs):

```
BridgeApi  <- Balbuffers <- Balbuffermanager
BridgeApi, Balbuffers <- Bal  (an RBusLogicalChannel on the "Hwa" LDD: DoControl / DoSvControl)
Bal, Balbuffermanager <- Gwc  (the gateway component: a CActive-based class, 33 exports)
Bal, Balbuffermanager <- <Codec>Gwc[TI] (RawGwc, AacDecGwc, AmrDecGwcTI, Mp3DecGwc) <- <Codec>HwDevice (MMF)
Bal <- Dasfgwc <- ASC1510.dll (the audio stream controller)
Bal <- DeviceManagementServer.exe; DeviceManagementServerProxy.dll (its client: z:\system\libs\DeviceManagementServer.exe)
BridgeApi <- DspMemMapper
```

- **No names anywhere** (stripped C++), so ordinals are named by what they call. EUser's exports are
  named from the SDK's `euser.lib` (`libords.py`: member `d1390s_<ordinal>.o` holds `__imp_<name>`);
  EUser's export table in this ROM is at **0x500E8938** (found by matching the XIP stubs against the
  compressed DLLs' EUSER ordinals).
- **XIP import stubs**: `ldr ip,[pc,#4]; ldr ip,[ip]; bx ip`, the literal pointing at the slot of the
  used DLL's **export table** (so the slot's position is the ordinal): `xan.py` names them.
- **Bal's DoControl functions** (Nokia/TI extensions of `d32hwa.h`): Bal@1 9, Bal@6 8, Bal@25
  0x80000000, Bal@8 0x80000003, Bal@11 0x80000005, Bal@10 0x80000006, Bal@24 0x80000008, Bal@17
  0x80000009, Bal@13 0x8000000E, Bal@14 0x8000000F, Bal@3 0x80000010, Bal@4 0x80000011, Bal@19
  0x80000014, Bal@5 0x80000015; DoSvControl: Bal@2 4, 5, 7; Bal@22 0x80000007, 6, 7; Bal@23 6, 7.
  Bal@9 → BridgeApi@12, Bal@20 / 21 → BridgeApi@15, Bal@28 loads / frees the Hwa LDD and PDD.
- **Each codec's Gwc holds its node's UUID** as a GUID struct (RawGwc: 781EB912-5631-11D6-ADBD-
  000086553665 = RAW_NOK; AacDecGwc, AmrDecGwcTI, Mp3DecGwc likewise).
- **Starting a node** (RawGwc@1, the clearest): create arguments in a TBuf8<32> + the UUID →
  **Bal@9** (→ BridgeApi@12: allocate the node); the streams' attributes (size 0xC02 or 0x800,
  timeout -1) → **Bal@21** (input 0, 1) / **Bal@20** (output 0, 1); buffers (0x1804, 0x1000 bytes)
  → **Balbuffermanager@4**; **Gwc@11** (the buffer manager); **Bal@2** (create: DoSvControl 4, 5, 7);
  Gwc@20 / @19 (the stream records); **Bal@22** (run: 0x80000007, 6, 7); Gwc@13; Gwc@31 with
  60,000,000 (a 60 s timeout). `lst_RawGwc.txt` from `lst.py RawGwc`.

To use a node from our own app: import libraries for Bal.dll / Gwc.dll / Balbuffermanager.dll by
ordinal (a .def with made-up names, `dlltool`), then the RawGwc sequence with the node's UUID; for the
JPEG decoder (1 input stream, no output stream: its output goes to a buffer mapped with DspMemMapper,
as Dspimgc does) also its create arguments and messages (TI's IJPD, unknown here).

### How MMF starts the RAW node (RawHwDevice → RawGwc), read for the probe

- `RawHwDevice.dll`'s ECOM table: implementation **0x101FAF3D** (NewL = its ordinal 2); its custom
  interface uid **0x101FAF3E** returns the CRawGwc.
- Its `CMMFHwDevice` vtable (GCC 2.9: 2 header words, then the functions), in **this** order (not the
  7.0s header's): ~dtor, **Start**(func, flow 1..4), **Stop** (Gwc@25(1,0)), **Pause** (Gwc@15),
  StopAndDeleteCodec, DeleteCodec (Gwc@2), **Init**(params), **CustomInterface**(uid),
  ThisHwBufferFilled, ThisHwBufferEmptied, **SetConfig** (RawGwc@3: the sample rates 11025-96000).
- `CRawGwc::NewL(observer, const TDesC16& name)` = RawGwc@2 (name "": `CBal::NewL("")` loads nothing
  yet); the object has 5 vtable pointers (multiple inheritance), the observer interface 7 functions.
- **Init's parameters are ~0x250 bytes** (Nokia's THwDeviceInitParams): the observer, per stream a
  block with a name descriptor (the DSP side's streams are `/dbpipe` devices) at +0x0C, +0x9C,
  +0x12C, +0x1BC, and a descriptor at +0x244. Init turns them into a **0x304-byte config** and calls
  the CRawGwc's first virtual = **RawGwc@1** with it: 4 stream blocks of 0xB0 at +0x0C (in 0),
  +0xBC (out 0), +0x16C (in 1), +0x21C (out 1); buffers at +0x2CC (0x1804 and 0x1000 bytes); the
  words at +0, +4, +8 go to Bal@2 (create).
- **Blocker:** those parameters come from DevSound's adaptation (not dumped), and RAW_NOK is the
  audio output path (DASF, the sync clock), so starting it outside MMF would compete with DevSound for
  the audio hardware. The JPEG decoder has no ARM-side user at all (no Gwc, no HwDevice in the ROM),
  so its create arguments and TI's IJPD messages would have to be guessed on the phone.

### Round 4 (Maps 1.49): DevSound

- `MmfDevSound.dll` runs **in the app's own process** and picks a HwDevice by its uid from a table
  (0x101FAF22, 0x101FAF26, 0x101FAF2A, **0x101FAF3D RAW**, 0x101FAF39, 0x101FAF93, 0x101FAF6B; PCM16 is
  FourCC " P16" 0x36315020).
- The order: `DeviceManagementServerProxy` object (0x64 bytes, its constructor, **@5** connect) →
  **@16 reserve**(proxy, HwDevice uid, mode 1 or 2, TBuf8<16> out: 16 bytes kept at DevSound+0x1C) →
  `REComSession::CreateImplementationL(uid, key offset 8)` → the HwDevice's **Start(2, 1)** (vtable +0x0C);
  later Pause (+0x14), StopAndDeleteCodec / DeleteCodec (+0x18 / +0x1C), CustomInterface (+0x24),
  the buffers (+0x28 / +0x2C); @21 release (modes 0, 3, 4, 5), @11, @13, @26.
- (Corrected: the first listings stopped at data inside the code; `xan.py` now uses capstone's
  `skipdata`.) DevSound **does** call the HwDevice's Init (+0x20) with its own +0xF4 as the
  parameters, after this DSP resource server sequence: @15, **@16 reserve**(uid, mode, TBuf8<16>) →
  DevSound+0x1C, **@3**(uid, mode, 0, …, &id at DevSound+0x388), **@17** (a size) and **@18** (an
  HBufC8 of that size: **the node's settings**, its TPtr8 kept at DevSound+0x338 = Init parameters
  +0x244), then **@29** (play) or **@2** (record) with the id. Init's parameters for play: the
  observer, stream D's word = 2 and name **"/mixer"** (+0x1B8, +0x1BC); for record stream C = 2,
  **"/xabus"** (+0x128, +0x12C).
- Live, from Maps 1.50 (DSP probe 2: a second of silence played with CMdaAudioOutputStream, the
  objects read from our own heap): CRawGwc's create arguments `07 00001F40 1 1 1 1 1` (8000 Hz);
  the stream attribute blocks `{1, 0xC02, 2, 0, -1, 0, 2, TBuf8<128> "/mixer"}` and
  `{3|1, 0x1000, 4|1|2, 0, 0, 1, 0|2, "/mixer"}`, i.e. TI's STRM attributes (segment, buffer size,
  buffers, alignment, timeout, mode, DMA channel) plus the device name.
- `ASC1510.dll` is the audio codec chip's controller (AIC23 / LM4855), not a DSP user.

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
`dcd.py` (every node's properties), `unz.cpp` (decompress an E32Image), `imports.py` (a compressed
DLL's imports by ordinal), `e32dis.py` (disassemble one, calls named), `xan.py` + `lst.py <Dll>` (the
ROM images in `files/rom/`, calls across them named), `calls.py` / `ctl.py` (per export: what it calls,
its DoControl numbers), `libords.py` (ordinal → name from an SDK .lib). Put the files in `files/`.

## What running our own code would take

A C55x compiler (TI's C5500 code generation tools), DSP/BIOS Bridge's DSP-side libraries to build a
dynamic node (DOF), and the ARM-side calls (from the 1.47 round: BAL / GWC / BridgeApi). Using an
existing node (e.g. the JPEG decoder for map tiles, in parallel with the ARM) needs only the ARM side
and the node's message protocol.
