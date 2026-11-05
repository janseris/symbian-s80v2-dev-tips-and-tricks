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
- Live, from Maps 1.51 (the real DevSound object at +0x94 = the RawHwDevice, +0xF0 = 0x101FAF3D):
  **the node's settings come from the DSP resource server**: DMS@18 returns a **0x308-byte blob**
  (`00000308`, then the 0x304-byte config Init hands to RawGwc@1): four stream blocks of 0xB0
  (`{1, 0x1000, 4, 0, 0, 1, 0, "/mixer"}`, `{1, 0x1000, 1, 0, 0, 1, 0, "/mixer"}`,
  `{1, 0x1000, 2, 0, 0, 1, 2, "/mixer"}`, ...). RawGwc then sets the in streams' buffer sizes (0xC02,
  0x800) and timeouts (-1). Init's parameters (DevSound+0xF4) are the HwDevice observer, empty name
  buffers, stream D's word 2 + "/mixer", and at +0x244 the TPtr8 of that blob.
- DMS@3 (register) takes an observer object (a heap object with a vtable; the server's events are
  delivered to it by an active object) and returns an id; DMS@29 (play) / @2 (record) use the id.
- `ASC1510.dll` is the audio codec chip's controller (AIC23 / LM4855), not a DSP user.

## Driving the DSP from our own code (Maps 1.52-1.54)

**Proven (Maps 1.53, DSP probe 3):** the RAW_NOK node's whole life from our own code, no sound API:

1. `DeviceManagementServerProxy` (called through its export table in ROM, **0x50924D34**): a 0x64-byte
   object, **@1** construct, **@5** connect.
2. **@16** reserve (uid 0x101FAF3D, mode 2, a TBuf8<16> `7F 2 3 3E8`) → 0.
3. `REComSession::CreateImplementationL(TUid 0x101FAF3D, 8)` → the RawHwDevice (vtable 0x50937224).
4. **@3** register (uid, mode 2, 0, an observer object, &id) → 0, id 4098 / 4099.
5. **@17** the settings' size (776) and **@18** the settings (a TPtr8 of an HBufC8).
6. **@29** play (id, &out) → 0.
7. The HwDevice's **Init** (vtable +0x20) with the 0x250-byte parameters (observer, stream D = 2 +
   "/mixer", the settings' TPtr8 at +0x244) → 0: the gateway's state 1, **the node runs**.
8. Teardown: **DeleteCodec** (+0x1C, Gwc@2) → 0 (state 0), delete (+0x08, flag 3), **@8**
   unregister, **@4** close. (StopAndDeleteCodec, +0x18, stopped Maps in 1.52: avoid it here.)

**Next (Maps 1.54, DSP probe 4):** the JPEG decoder node through our own CBal (Bal.dll's export
table **0x5090FFD0**): `CBal::NewL("")` @12 (a TPtrC16 in two words), allocate **@9** ({TPtrC8 create
arguments, TUint8* UUID}), create **@2** ({pointer, cfg0, cfg1, cfg2}), delete **@23**, the CBal's
virtual destructor (flag 3).

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

## Probes without installing (Maps 1.58) and what they measured

Maps 1.58 loads a probe DLL from the PC (`maps9300/probe/`, `build_probe.sh`) and runs it in a
thread: no install per test (Symbian 7.0s loads a DLL from any path).

**dspprobe 1:** the JPEG decoder node is created when its input stream 0 is connected first
(Bal@21: kind 1, `"/dbpipe"`, 0x1000 x 2, timeout -1) and runs (@22) and deletes (@23) cleanly.

**dspprobe 2** (ARM at ~150 MHz, one repetition each):

| What | Time |
|---|---|
| transform 1000 vertices, 32-bit (9 mul) | 0.55 ms |
| the same with 64x32-bit products (`long long` x `int`: umull + 2 mla) | 4.3 ms (a plain 32x32->64 is one smull) |
| project 1000 vertices (2 divides each) | 1.3 ms |
| fill 640x200 16-bit | 4.0 ms (~64 MB/s written) |
| z-buffered flat span 320x200 | 9.0 ms |
| affine textured span 320x200 | 12.7 ms |
| copy 256 KB | 10.3 ms (~25 MB/s) |
| a call into the DSP driver (the node's attributes, Bal@8) | 17 us |
| DspMemMapper: reserve 64 KB of DSP space, map our buffer | 0 / < 1 tick; DSP address 0x360000 |
| ARM cache flush of 64 KB (DspMemMapper@2 -> BridgeApi@33) | 165 us |

So the vertex work is cheap on the ARM; a frame's cost is the pixels (memory bound). The DSP
could only help by drawing part of the pixels in parallel (its internal RAM, DMA out), which
needs our own node.

The DSP calls (found for the probes): Bal@19 PutMessage and Bal@5 GetMessage take a TDes8 of
12 bytes `{cmd, arg1, arg2}`; Bal@11 registers for notification; Bal@8 the node's attributes
(0x10C bytes); Bal@1 the processor's info; Bal@7 the processor (CBal+4), which
`DspMemMapper::NewL(processor, entries)` (@6) takes; @7 reserve `{index, size}`, @5 map
`{ARM address, size, attributes, index}, remap`, @3 the DSP address, @2 flush `(address, size)`,
@8 unmap, @1 unreserve. DspMemMapper's export table: 0x50911BAC.

## Our own DSP code: the compiler

TI's C5500 code generation tools 4.4.1 (`ti_cgt_c5500_4.4.1_setup_linux_x86.bin`, from TI's
download archive, behind an export self-certification; don't commit it) install with
`--mode silent --prefix <dir>` on x86-64 Linux with `libc6:i386`. Its tools are static 32-bit binaries; where 32-bit programs can't run (Cowork's Linux VM: "Bad system call") they run through `qemu-i386-static` (user mode, no root): `setup_cgt55.sh <the installed tree, tar'ed> [qemu-user-static .deb]` gives each tool a folder with wrappers for the others (the drivers `cl55` and `masm55` start their siblings from their own folder). `cl55 -v5510
--memory_model=large -O2 -c` gives TI-COFF (large model, c55_std calls, R_REL24 relocations to
`_NODE_getMsg` etc.): the same relocations, with the same type numbers, the ROM's DOF nodes carry.

## Our own node: COFF -> DOF, registration, the node API (dspprobe 3: it runs)

**The DOF format exactly** (`dofw.py` reads and writes it; all 21 ROM nodes come out byte for byte
the same). Linux's `drivers/staging/tidspbridge/dynload/doff.h` and `cload.c` (v3.4) have the
structures and the loader's checks:

- Header 36 B: string table size, entry, `0x00010203`, the string table's size up to the last
  section name, then u16s: symbols, the longest string (with its NUL, not the file name),
  sections, sections to allocate, DOFF version 0, target 0x9C (C55x); flags u16 0x12E0 (big-endian
  target), entry section s16; a checksum word: the 9 words sum to 0xFFFFFFFF.
- Verify record 20 B: time, then ~sum of the section headers, of the string table, of the
  symbols, and a last word that makes the record sum to 0xFFFFFFFF.
- String table: the file name, the section names, the symbol names.
- Section headers 28 B: name offset, run and load address (`.text` at 0x100 in TI's files),
  size (bytes, data sections too), page, flags (bits 0-3 type, 0x10 allocate, 0x20 download,
  bits 8-11 log2 alignment: `.text` 0x230, `.const` 0x231, the bridge's sections 0x101), the first
  packet's file offset (0 for an empty section), packets.
- Symbols 12 B: name offset (-1: none), value (load address), section (1-based; 0 undefined),
  class (2 external, 3 static: a section's own symbol for relocations against it).
- Packets: {relocations, size, checksum} + data (up to 1024 B, padded to 4) + relocations 12 B
  {offset in the packet, symbol, disp u16, type u16}: TI-COFF's relocation types as they are
  (5 = R_REL24 for `CALL`, 124 = R_LD3_REL23 for a data address in words). The whole packet
  sums to 0xFFFFFFFF.
- The bridge's sections (UTF-16BE, not loaded): `.dspbridge_symbols` (the RMS/SHM symbols, then
  the node's three functions), `.vers`, `.dcd_register` (`UUID:0,`, 0 = a node), and `.<UUID>`
  with the node's DCD properties: `1024,UUID,NAME,01H(task),00H,1024,0200H,080H,0c00H,05H,03H,
  03e8H,064H,0aH,<priority>,<stack>,<system stack>,00H,<message depth>,<inputs>,<outputs>,
  0ffffffffH,NAME_create,NAME_execute,NAME_delete,00H,08000H,iAlgName,1,0ff3f3f00H,0ff3f3f82H,`.

`coff2dof.py in.obj out.dll55l --uuid ... --name ...` builds one from cl55's object (.text only
for now: no data sections, no relocations against our own sections). Placed by hand at a made-up
address with the base image's symbols, the relocated calls disassemble (dis55) to
`CALL #0x2b55f8` = `_NODE_getMsg` etc.

**Registering a node** (no ROM code does it for the plugins we know of; BridgeApi has it):
`Bal@16(CBal*, const TUint8 uuid[16], TInt type, const TDesC16& file)` = `BridgeApi@14` on the
CBal's manager (+0x24) = DCD_RegisterObject: it opens the file, then the driver's DCD (DoSvControl
0x4000001E + 2) keeps UUID -> file. `BridgeApi@16(manager, uuid, type)` unregisters. The CBal has
to be attached first: its internal 0x5090FB68 (which Bal@9 calls: the drivers, BridgeApi@13 the
processor, BridgeApi@5 the manager). The UUID bytes as a GUID (data1..3 little-endian); the
bridge finds the properties in the section `.` + `%08X_%04X_%04X_%02X%02X_%02X...` uppercased.
`BridgeApi@8`/`@9`: the node / processor enumerations; `@7(processor, file, 0)`: load a base image
(it registers that file's `.dcd_register` and resets the DSP: not for us).

**The node API on the DSP** (from Prodtest's code through dis55, which disassembles it exactly
once wrapped in a COFF):
`RMS_WORD NAME_create(Int argLength, Char* argData, Int numIn, RMS_WORD* inDef, Int numOut,
RMS_WORD* outDef, NODE_EnvPtr node)`, `RMS_WORD NAME_execute(NODE_EnvPtr)`,
`RMS_WORD NAME_delete(NODE_EnvPtr)`, all returning RMS_EOK = 0x8000 (32-bit, in AC0); the
node's context pointer at `node + 12` words. `Bool NODE_getMsg(node, RMS_DSPMSG*, Uns timeout)`,
`NODE_putMsg(node, NULL /* to the GPP */, RMS_DSPMSG*, Uns timeout)`, timeout 0xFFFF = forever,
`RMS_DSPMSG` = 3 x 32 bits {cmd, arg1, arg2}; cmd 0x80000000 = RMS_EXIT (end execute).
`MEM_valloc(segid, size, align, value)` with `SARAM_HEAP` / `DARAM_HEAP` / `EXT_HEAP` from the base
image. The base image exports 1485 symbols (`_CLK_getltime`, `_memcpy`, `_HWI_disable` ...).

**On the ARM side**: `Bal@19(CBal*, TDes8* 12 bytes)` puts a message, `Bal@5(CBal*, TDes8*)` gets
one (GWC waits for Bal@11's notification first).

**Registration needs two entries**: the UUID as a node (type 0: the DCD properties) and as a
library (type 2) to the same file: allocating looks the code up as a create library (3), then a
library (2) (BridgeApi 0x507C4F9C), else -6. Don't put RMS_EXIT (0x80000000) with Bal@19 yourself
(it hung); delete (Bal@23) ends the node.

**dspprobe 3 (Maps 1.58, 2026-11-04): our code runs on the DSP.** Plain C (cl55 -O2, `volatile`
loops, no intrinsics, no DMA):

| What | DSP | ARM |
|---|---|---|
| a message round trip (put + get) | 189 us | |
| 3x3 Q14 transform, vertices on the DSP's stack | 171 ns a vertex | 549 ns |
| fill SARAM (volatile loop) | 15 words/us (slow C: to redo) | |
| read our mapped buffer (SDRAM) | 5.5 MB/s | |
| write it | 11.3 MB/s, words in ARM order (no swapping needed) | ~64 MB/s fill |
| transform 8192 vertices in our buffer (+ flushes, round trip) | 1192 ns a vertex | 549 ns |
| textured pixels 160x100, texture + picture in SDRAM | 533 ns a pixel | 198 ns |
| texture in SARAM, picture in SDRAM | 213 ns | |
| texture and picture in SARAM | 144 ns | |
| the ARM filling 320x200 x20 while the DSP draws into SDRAM | 3x slower (47 -> 141 ms); the screen shook | |
| the same while the DSP works in SARAM only | no change (47 ms) | |

**dspprobe 4: the same written for speed** (no `volatile`: cl55 makes `RPT`/`RPTBLOCAL` loops
and `MACK`s), buffers of 4096 words from `SARAM_HEAP` / `DARAM_HEAP`:

| What | DSP | before | ARM |
|---|---|---|---|
| fill / copy in SARAM or DARAM | ~150 words/us (1 word a cycle: the DSP at ~150 MHz) | 15 | |
| 3x3 Q14 transform, DARAM | 163 ns a vertex | 171 | 549 |
| textured pixels, texture DARAM, picture SARAM | 102 ns a pixel | 144 | 198 |
| SDRAM -> DARAM, 8 KB block copies | 9.0 MB/s | 5.5 | |
| DARAM -> SDRAM | 12.8 MB/s | 11.3 | ~64 (fill) |
| the ARM's 320x200 fills while the DSP reads SDRAM | 4.7x slower | | |
| ... while it writes SDRAM | 2.7x slower (the screen shakes) | | |
| ... while it works in DARAM | no slower | | |

The DSP's own work got faster; its SDRAM traffic didn't: the limit is the path to the SDRAM (one
word at a time through the traffic controller), not the code, and every such word stalls the ARM
and the LCD's refresh. Untried: the DSP's DMA (ACPY2 / DMAN, as the video and JPEG nodes use it),
which may move bursts at a better rate.

**dspprobe 5: the DSP's DMA works, ~5-7x the CPU's SDRAM rate.** As the video and JPEG nodes do,
with the base image's XDAIS DMA (no TI libraries of ours): `DMAN_init()`, `ACPY2_init()`, then
`DMAN_addAlg(alg, fxns)`: `fxns` an IDMA2_Fxns {implementationId, dmaChangeChannels,
dmaGetChannelCnt, dmaGetChannels, dmaInit} (pointers, 2 words each), `alg` a struct whose first
word points to a struct starting with the same implementationId (DMAN asserts it). It asks
`dmaGetChannelCnt()` (1), `dmaGetChannels(alg, recs)` (records of 4 words {handle, queueId};
queue 0 as the MPEG-4 decoder uses 0-2), allocates, and gives the channel handle through
`dmaInit(alg, recs)` (return 0). Then `ACPY2_configure(handle, int params[7])` = {0 (1D->1D),
element size (1 16-bit, 2 32-bit), frames 1, 0, 0, 0, 0}, `ACPY2_start(handle, src, dst, count)`
with **byte** addresses as longs (a DARAM pointer x2; DspMemMapper's address as it is) and the
element count, `ACPY2_wait(handle)`. At the end `DMAN_removeAlg(alg, fxns)`, `ACPY2_exit()`,
`DMAN_exit()`. Our functions' addresses need coff2dof's expression relocations (TI's RE_PUSH etc.,
as the ROM nodes have them).

| 8 KB by DMA (16- or 32-bit elements alike) | time | rate | the CPU's |
|---|---|---|---|
| DARAM -> SARAM | 35 us | 232 MB/s | 305 MB/s |
| SDRAM -> DARAM | 183 us | 44.8 MB/s | 9.0 |
| DARAM -> SDRAM | 95 us | 85.9 MB/s | 12.8 |
| the ARM's 320x200 fills while the DMA reads SDRAM nonstop | 2.3x slower | | 4.7x at 1/5 the data |
| ... while it writes SDRAM nonstop | 4.7x slower | | 2.7x at 1/7 the data |

So a 320x200 16-bit picture (128 KB) goes out in ~1.5 ms, 1000 vertices (6 KB) in ~0.13 ms: the
DSP can work on its own RAM and exchange whole buffers with the ARM each frame.

So: the DSP is ~3x the ARM at arithmetic and as fast at pixels from its own RAM, runs in
parallel, but its SDRAM access is slow and stalls the ARM (and the LCD's refresh: the picture
shakes). Coprocessor jobs must keep their data inside the DSP and move little: small inputs and
outputs per message, or the DSP's DMA (untried).

## 3D drawing on the DSP (dspprobe 6-15, Maps 1.59): measured, and why it doesn't pay

Maps 9300's textured triangles split between the ARM and our node, every frame checked to the bit
against the ARM's own drawing. The code: `maps9300/dsp/` (`verts2.inc`, `raster.inc`, `rows3`-`rows7.inc`,
`prep6.inc` + `prep6asm.inc`), host tests in `dsp/test/`, probes in `maps9300/probe/` (archive/).

| What | Measured |
|---|---|
| The DSP's clock (a `RPT` loop timed by the ARM) | ~145 MHz |
| The instruction cache (ST3_55 CAEN) | on; code in SDRAM (0x280000) runs as fast as a copy in SARAM (+5 %) |
| A textured pixel, texture in the DSP's RAM | 11 cycles (two independent lanes: 7) |
| A textured pixel, texture in SDRAM (read by the CPU) | 48 cycles |
| Per triangle in C (edges + rows set-up), cl55 -O2 | ~800 cycles; with the edges set up on the ARM (`prep6`) ~half |
| `__mpyli` (32x32 multiply) calls | the compiler's for every `long * long`: use `_lmpyu` / `_lmpysu` pieces |
| The ARM writing the shared (mapped) buffer | ~60 MB/s, as its own memory; reading ~38 MB/s |
| Both at once, the DSP reading SDRAM non-stop | the ARM's work ~2x slower (one memory) |

Synthetic scenes (one 128 x 128 texture in the DSP's RAM): with ~20-40 px triangles the split won ~1.7x
(ARM 49 ms alone; ARM set-up 29 ms in parallel with the DSP's 28 ms). A **real** frame (Maps' dump of
Prague's Old Town, LoD 21, 320 x 200: 8,000 triangles, half of them 4.5 px or smaller, 16-30
textures, 2-3 MB) doesn't fit that: the textures can't be in the DSP's RAM, so 48 cycles a pixel, and
the DSP took 130 ms against the ARM's 135 ms in the probe (Maps' own drawing: 92 ms), and with both
running the ARM's share went from 94 to 195 ms. So the 3D view stays on the ARM; the DSP is for work
that streams through its own RAM by DMA with no random reads of SDRAM (a video's YUV to RGB, say).

Pitfalls met: our node's data must be `.text` only (no `.bss`); a DSP read of an unmapped address
(a record with a garbage texture address: the frame was DMA'd over the records) restarted the
phone; `C:\System\Temp` is emptied when the phone starts (a probe's progress file there is gone after a
crash: `C:\Data\...`); a probe's lines reach Maps' log only when it ends.

## The 3D geometry on the DSP (dspprobe 16-17e, Maps 1.59)

The other half of Maps' 3D frame: the corners projected (`r3_verts`), the triangles kept (on the screen,
facing us) and their records built, ~64 ms of the ARM's ~137 ms frame at street level. On the DSP it
streams: the tiles' arrays in by DMA, records out by DMA, nothing read at random from SDRAM. The idea:
a pipeline, the DSP doing frame N+1's geometry while the ARM draws frame N.

| What (Old Town LoD 21 dump: 22 tiles, 31,061 corners, 42,411 faces) | Measured |
|---|---|
| DMA traffic like the DSP's, against the ARM drawing (dspprobe 16) | the ARM +14 % at 27 % of the time, +29 % at 54 %, +55 % non-stop |
| DMA rates | 44.8 MB/s into the DSP, 85.9 MB/s out |
| The ARM (Maps' assembly) | 68 ms (corners 34) |
| The DSP in C, cl55 -O2 (dspprobe 17) | 126 ms (corners 79); the projection in 40-bit accumulators (17d) 116 ms |
| The DSP in assembly (17e): corners (verts4b) | 22.4 ms (67.5 in C); 19.6 with the next block's DMA overlapped |
| ... the faces and records (faces4) | 34.7 ms (47.7 in C); 28.6 overlapped; 18.6 with the uv left to the ARM |
| A frame's geometry, all of it in assembly, overlapped, uv on the ARM | 38.3 ms (C 115 ms; the ARM 68 ms) |
| The DSP's frame and the ARM's own geometry at once | 76.4 ms a pair (the ARM alone 67.7): the DSP's work hidden, the ARM ~13 % slower |
| The ARM filling the records' uv from the mapped buffer | 14.9 ms (8000 records: slow, the mapped memory) |
| DspMemMapper at once | 8 MB maps (DSP 0x360000); 16 MB: reserve -6 (KErrArgument) |
| Self-test (8192 random corners) and the frame's 8000 records | 0 differences in every variant |

C on the C55x is slow here for reasons the compiler can't help: `int` is 16 bits (every 32-bit
product a call or a `_lmpy*` intrinsic in pieces), each `if` a branch costing 5 cycles even when not
taken, and status-bit juggling (FRCT, M40) around its 17-bit multiplies. In assembly a corner is ~75
instructions with no branch (conditional execution instead), a rejected face ~20.

### Hand assembly for the C55x without a simulator

TI's C55x simulator (SPRU599D) comes only inside older Code Composer Studio releases for Windows; TI's
forum says the Linux CCS 5 never had it. What we did instead (`maps9300/dsp/`):

- **The assembler** (cl55 through qemu) catches syntax, illegal parallel pairs and the silicon
  exceptions: assemble the file alone with `--silicon_core_1_0 ... _2_2` and without the compiler's
  `.noremark` lines to see them.
- **A text-level interpreter** (`dsp/test/sim55.py`) of just the instructions used, written from
  SPRU374G's descriptions, run against the C on the host (`v4test.py`, `f4test.py`), with mutation
  checks that it does catch a wrong shift or condition; parallel pairs are executed in both orders and
  must agree (they mustn't depend on each other).
- **On the phone**: a self-test command (assembly against C on random inputs, the first difference
  reported word by word), then the real frame's records against the ARM's.

What we learned on the way (SPRU374G, SPRU371F):

- Calling convention (cl55 4.4, large model): data pointers in XAR0, XAR1, ... XAR4 in order, 16-bit
  ints in T0, T1, longs in AC0-AC2; return in T0 (int) or AC0 (long); save T2, T3, XAR5-XAR7. The C
  environment has M40 = 0, FRCT = 0, SATD = 0, SXMD = 1, CPL = 1, ARMS = 1: set M40 for 40-bit
  intermediates and clear it on the way out. Copy the compiler's prologue: it puts two NOPs after the
  first `PSHBOTH` (silicon exception CPU_7).
- Assembly in the node: `asm("...")` lines in the C file (our `build_dsp.sh` makes them from a `.s55`
  file), since `coff2dof.py` takes one object. No data: constants as code.
- Multiplies are 17 x 17 bits with a "32-bit result": an accumulator operand is its bits 32-16, so a
  17-bit value goes in as `v << 16`, and `(v * 2^14 + r) << 2` already has `v` in bits 32-16 (no
  separate floor). An unsigned 16-bit value also fits as a 17-bit operand. Keep every product under
  2^31.
- Branches: `BCC` takes 5 cycles not taken, 6 taken; `B` 6. `XCCPART cond` before an instruction
  makes it conditional for 1 cycle (a store's condition is read in the R phase, a register op's in X;
  pointer post-modifications happen anyway). `RPTB` loops cost nothing; a branch out ends them.
- ARMS = 1 (the compiler's mode): offsets `*ARn(short(#1..7))` and the index `*ARn(T0)` only (no T1);
  a 16-bit offset `*ARn(#k)` can't be in a parallel pair; two memory operands in a pair must be
  Xmem/Ymem modes (`*ARn`, `*ARn+`, `*ARn-`, ...), no offsets.
- Writing an AR in the X phase and addressing with it (AD phase) needs ~4 instructions between them or
  the pipeline stalls (it's protected: slower, not wrong).
- Rev 2 cores do address arithmetic in 16 bits: a buffer mustn't cross a 64K-word page (checked
  before calling the assembly, which then falls back to C).
- `dbl(Lmem)`: the high word at the even address.

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
For our own nodes: `setup_cgt55.sh` (TI's compiler through qemu-i386), `coff.py` (TI-COFF reader),
`dofw.py` (DOF reader / writer), `coff2dof.py` (an object -> a node DOF).

## What running our own code takes

TI's C5500 code generation tools (free), `coff2dof.py`, and the ARM-side calls above: no TI
DSP-side libraries are needed, the loader links the node against the phone's base image. A
node without data sections runs today (dspprobe 3's echo node); data sections need the
relocations against our own sections (a partial link, or adjusting the addends).
