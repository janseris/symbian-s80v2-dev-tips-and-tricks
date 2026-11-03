# Networking on the 9300

From the Maps 9300 notes (moved from `symbian-s80-build-tools/native9300/README.md`, 3 Nov 2026). Paths like `maps9300/` are the sibling repos in the same folder.

## 11. Big uploads over GnuBox (Bluetooth)

Measured with Maps 9300 1.44-1.46 (the full report: `localserver/FOR-OTHER-CHATS-uploads.md`):

- A multi-KB POST on a **kept-open** connection stalls over GnuBox: the first one on a new connection
  arrives, the next one on the same connection sends 16 KB (one send window) or nothing, then waits
  until the link drops. Send each big upload (over ~1 KB) on a **fresh connection** and close it
  after the response; small requests can keep reusing connections.
- With that, uploads run at ~30 KB/s (31 files, 1.5 MB in 24 s); a new connection costs ~0.2-0.3 s.
- Keep a download slot free for an upload that waits (tile requests otherwise take every freed slot),
  show progress, allow stopping, and log each step straight to the log file.

## The full report: big uploads over GnuBox

Written 3 Nov 2026 from Maps 9300 1.44-1.46 (sending 31 ROM files, 1.5 MB, to `ota_server.js`
`/results`), with GnuBox Share's logs (`gnubox-s80/host/windows-cs/logs/requests-2026-11-03.jsonl`,
`gnubox-share-2026-11-03.log`) and the phone's log.

## What happened

- The **first** big POST on a **new** TCP connection always arrived (28 KB in ~1 s).
- The **next** big POST on the **same kept-open** connection stalled:
  - 1.44: it sent exactly 16 KB of the body (the phone's TCP send window) and then nothing more
    (requests.jsonl #51, #61: `up 16654`, "no response", ended by "link closed" minutes later).
  - After the log's own POST (6.8 KB) on a connection, the next POST on it stalled at 16.9 KB (#69).
  - 1.45: the next POST sent nothing at all; GnuBox showed the connection open and idle for minutes.
- On the phone, each stuck write ended at Maps' 20 s I/O timeout (plus a retry), so its counter went
  on ("one file a minute") while nothing reached the PC. Meanwhile the stuck job held the download
  thread that does non-tile work, so the log couldn't be sent and the map's own requests waited.
- Small requests (GETs, small POSTs) on kept-open connections were never affected.

Where exactly it sticks (the phone's Symbian TCP stack after the connection went idle, or GnuBox's
user-space TCP in `Nat.cs` when the phone sends a multi-segment body on a reused connection) isn't
known yet: a question for the GnuBox chat. GnuBox's receive window is 64 KB and it acks every
segment, so look at what happens to the phone's second burst (retransmits? window probes? acks
that don't reach the phone?).

## The fix that works (Maps 1.46)

- A POST with a body over 1 KB goes on a **fresh connection**, closed right after the response
  (`net.cpp`, `FetchOnceL`: `bigPost`). Small POSTs and GETs still reuse connections.
- Result (1.46 over Bluetooth): **31 files, 1503 KB, all 200 OK, in 24 s**: ~30 KB/s up
  (Rv8_decoder 237 KB in 8.0 s, Dsp_image.dof 193 KB in 7.6 s); a new connection costs ~0.2-0.3 s.

## Tips for any app on the 9300 that uploads

1. **Big uploads: one fresh connection each, then close it.** Don't send a multi-KB body on a
   kept-open connection over GnuBox.
2. **Keep a slot / thread free for the upload.** Maps' tile requests took every freed download slot
   first, so the upload waited for ever; now one slot stays free while an upload waits.
3. **Show progress, and allow stopping** (the same menu item again).
4. **Log each step straight to the log file** (flushed), so a stuck run can be read after a restart.
5. **Log each upload's result and time**, and say when one takes over 60 s.
6. Uploading to `ota_server.js`: `POST /results?name=<letters, digits, _ ->&ext=<1-5 letters/digits>`
   saves the body as `uploads/<time>_<name>.<ext>` (binary is fine; `ext=txt` is also printed).
7. A JSON body to Mapy.com's GraphQL (`vectmap.mapy.cz/mediaagg/gql`) needs
   `Content-Type: application/json` (text/plain: 415).
8. Upload speed to expect over GnuBox Bluetooth: ~30 KB/s; download was ~15 KB/s per tile stream.

## Bluetooth speed over GnuBox: what limits it (GnuBox chat, 2-4 Nov 2026)

Measured with GnuBox Share (the Windows PC side of GnuBox, `gnubox-s80/host/windows-cs`; its logs
give per second: speed, the phone's advertised TCP window, round trip, how often the window was
full) and NetTest (`gnubox-s80/nettest`: downloads test files from the PC with every combination
of parallel connections and TCP window). Details: `gnubox-s80/notes/06-test-log.md` #16-#19.

- **The ceiling is ~34-35 kB/s of payload, whatever the TCP settings.** NetTest, plain HTTP from
  the PC (no TLS, no internet server, no decoding), 755 KB a run:

  | Connections | Window | Link speed | Round trip (avg) |
  |---|---|---|---|
  | 2 | 8 KB | 32.9 kB/s | 358 ms |
  | 2 | 16 KB | 33.8 | 530 ms |
  | 2 | 32 KB | 33.8 | 612 ms |
  | 2 | 64 KB | 34.2 | 624 ms |
  | 3 | 16 KB | 34.4 | 842 ms |
  | 3 | 32 KB | 34.4 | 1145 ms |
  | 1 | 16 KB | 30.0 | 379 ms |
  | 1 | 64 KB | 30.4 | 146 ms |

  Even with 8 KB windows full all the time the speed didn't drop: the limit is below TCP. **So over
  Bluetooth use 2 connections and an 8-16 KB window**; bigger windows and more connections only
  add delay for everything else loading at the same time. One connection loses ~10 % to the pause
  between files. (The old figure "20-30 kB/s because of the 8 KB default window" was the apps,
  HTTPS and the servers, not the window.)
- **Not the radio either.** The same ~35 kB/s came from two different hosts (Android + BlueDUN++:
  Maps' byte counter 34.6-35.7 kB/s; Windows + GnuBox Share: 34-37 kB/s), only ~39 % of
  Bluetooth 1.x's 723 kbit/s (~90 kB/s one way). The likely cause is the phone's Bluetooth serial
  driver **BTCOMM.CSY** (Symbian's published source, a 2009 version that may differ from the
  9300's): it keeps **one** socket read of at most 1 KB outstanding, into a 4 KB buffer, and stops
  reading at 3 KB until PPP drains it to 2 KB. With this phone's 666-byte RFCOMM frames (L2CAP's
  672 minus headers), 35 kB/s is one read cycle every ~19 ms. Not proven: that needs a different
  serial driver (a CSY of one's own, possible with the SDK's `cs_port.h`).
- **Bluetooth costs the CPU:** ~45 % at 35 kB/s (Maps 9300's benchmark: decoding ran at ~51-58 %
  of its USB speed). With a CPU-heavy app downloading too (Maps' 3D view + a browser download), the
  phone, not the link, is the limit: both together got ~14 kB/s and the round trip reached 2.8 s.
- **Small files are slow because of each new download's fixed costs**, not a slow start: GnuBox
  Share sends at full speed from the first second. NetTest 1.2's small-file test (plain HTTP from
  the PC, 8 files each of 2 / 5 / 10 / 20 / 50 KB, median time per file on the phone):

  | Connections | Per file | Overall | 2 KB | 5 KB | 10 KB | 20 KB | 50 KB |
  |---|---|---|---|---|---|---|---|
  | 1 | kept open | 27.7 kB/s | 125 ms | 203 | 390 | 671 | 1578 |
  | 1 | new for each file | 14.3 kB/s | 734 ms | 812 | 1000 | 1312 | 2203 |
  | 2 | kept open | **30.7 kB/s** | 562 ms | 656 | 453 | 1406 | 2406 |
  | 2 | new for each file | 29.0 kB/s | 984 ms | 390 | 546 | 1484 | 2328 |
  | 3 | kept open | 30.1 kB/s | 750 ms | 765 | 953 | 2015 | 3859 |

  - **A new TCP connection costs ~0.6 s over Bluetooth** (plain HTTP; with one connection it halves
    the throughput of small files). For HTTPS add the TLS handshake: 1.7-11 s in Maps' benchmark.
    **Keep connections open, reuse TLS sessions.**
  - On a kept-open connection a file takes ~0.1 s + its size at ~32 kB/s: one round trip is the
    fixed cost.
  - **2 connections kept open give the most in total**; they also hide most of a new connection's
    cost (29.0 vs 30.7 kB/s). 3 connections add nothing but make each file wait longer (a 50 KB file
    3.9 s instead of 1.6 s): for what the user waits for (the next visible tile, the page's own
    files), fewer connections finish each item sooner.
  - An app's displayed speed rises slowly at the start only because these fixed costs are counted
    in.
- **The TCP receive window:** `RSocket::SetOpt(KSoTcpRecvWinSize, KSolInetTcp, n)` before
  `Connect` works (GnuBox Share saw the phone advertise exactly 8160 / 16320 / 32640 / 65280 B).
  The default for apps that don't set it is 8 KB. The stack (`TCPIP6.PRT`) reads an ini section
  `[tcp]` with `tcp_recv_buf`, `tcp_send_buf`, `tcp_winscale`... from `tcpip.ini` (the key names
  and the section are in its strings); GnuBox's *Bigger TCP window* writes
  `C:\System\Data\tcpip.ini` - whether the stack reads the C: copy is not confirmed yet.
- **The serial port's rate is not enforced:** GnuBox's ModemBearer says 115 200 bit/s
  (~11 kB/s), yet 35 kB/s flow. Don't read the CommDb rate as the link speed.
- **PPP compression:** with the ISP record's header and software compression on, the phone asks
  for **Stac LZS** (CCP) and **Van Jacobson** header compression. Little to gain today: pages come
  gzip'd, almost everything is HTTPS, pictures and tiles don't compress; VJ would save ~3 %.
- **Measure downloads by the phone's clock or per second on the link**, not by a PC-side request
  record: the PC side ends when it has handed the last bytes on, seconds before the phone has them
  (a 327 KB download "took" 7.3 s by GnuBox Share's request record, ~9.2 s of data per second).

## Bluetooth errors (-6000 and below)

From the SDK (`hcierrors.h`, `bt_sock.h`); GnuBox 2.8 shows them in words.

| Code | Meaning | What helps |
|---|---|---|
| -6000 minus *n* | HCI error *n* of the phone's Bluetooth chip | |
| -6003 | hardware failure (after a day of use: the phone couldn't open a link at all) | turn Bluetooth off and on (no restart needed) |
| -6004 | page timeout: the other device didn't answer | in range? its Bluetooth on? |
| -6005 / -6006 | authentication failure / link key missing | pair again |
| -6012 / -6031 | command disallowed / unspecified (-6031 also: a PC Suite link is up and blocks it) | turn Bluetooth off and on; close PC Suite |
| -6016 / -6019 | the other side stopped answering / ended the connection | |
| -6023 | repeated attempts | wait a minute |
| -6300 - *n* | L2CAP: -6304 connect failed, **-6305 link lost** (not "service not found"), -6310 the other side disconnected | |
| -6350 - *n* | RFCOMM: -6354 frame response timeout, -6355 the other side closed the channel | |

## Android as the host (BlueDUN++)

- BlueDUN++ stops sharing ~70 s after the Android phone's screen turns off, even with battery
  optimisation off in the settings. What fixes it: `adb shell dumpsys deviceidle whitelist
  +com.bluedunz` (once, from a PC with USB debugging; again after reinstalling the app).
- The 9300 has no Bluetooth PAN: Android's normal Bluetooth tethering can't work; it needs dial-up
  (DUN) over a serial channel, which BlueDUN++ provides and GnuBox uses.
