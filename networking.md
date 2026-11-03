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
