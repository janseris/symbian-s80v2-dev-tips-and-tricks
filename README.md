# Symbian Series 80 v2: development tips and tricks

Findings, measurements and tips for native development on Symbian **Series 80 2.0** (Nokia 9300 and
9500 Communicators, Symbian 7.0s, EKA1, TI OMAP1510), learned while building Maps 9300, MP4 Player,
Browser 9300, GnuBox for S80 and other apps. Series 80 v1 (Nokia 9210, Symbian 6.0) isn't covered,
though some of it may apply.

The tools to build apps (GnuPoc, GCC 2.9, the ARM emulator kit, reusable code, the compiler's
pitfalls) are in [symbian-s80-build-tools](https://github.com/janseris/symbian-s80-build-tools).

| File | What |
|---|---|
| [performance.md](performance.md) | The 8 KB data cache (measured: a miss ~265 ns, a hit ~1.5 cycles), what made a 3D renderer faster, JPEG decoding |
| [networking.md](networking.md) | Network speeds, big uploads over GnuBox (Bluetooth): use a fresh connection for each, ~30 KB/s up |
| [from-the-apps.md](from-the-apps.md) | Tips the other native apps found (speed, the UI, files, the network, audio and video) |
| [wikibooks-tips.md](wikibooks-tips.md) | From the Wikibooks Series 80 page: key scan codes and more (not all checked) |
| [dsp/](dsp/README.md) | The C55x DSP: what's in the ROM (the TI codec nodes, the bridge, Nokia's GWC / BAL framework), the file formats, analysis scripts |

Nokia's and TI's files (ROM images, DSP programs) are never committed: put them in `dsp/files/`,
which is ignored.
