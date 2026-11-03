# Small API notes (Symbian 7.0s, EKA1, GCC 2.9)

Things that cost a build or a crash, found while writing GnuBox, AudioProbe, FileFetch and
NetTest. The bigger compiler pitfalls are in `symbian-s80-build-tools/native9300/README.md`.

- **`cond ? &_L("a") : &KNullDesC`**: GCC 2.9 warns "taking address of temporary", and it's a
  real bug (the `TPtrC` is gone after the statement). Use `_LIT` constants and cast both sides to
  the same type: `cond ? &(const TDesC&)KTextA : &(const TDesC&)KNullDesC` (or `TDesC8`).
- **`Window().Invalidate(rect)`** (redraw only a part, e.g. a status line once a second instead of
  `DrawNow()` on the whole view) and `RWsSession::Flush` need **`ws32.lib`** in the `.mmp`;
  without it the link step fails with only "Error 1" from make.
- **Redraw only what changed.** A once-a-second `DrawNow()` on a view with a list box redraws the
  whole screen: CPU taken from everything else (Bluetooth takes ~45 % already). Invalidate the
  changed rectangle; the window server then draws only the controls in it.
- **`TInt64` is a class on EKA1**: no `long long` arithmetic in the API. `d.Int64()` of a
  `TTimeIntervalMicroSeconds`, divide with `v /= TInt64(1000)`, read with `v.GetTInt()`
  (`I64INT(v)`); `TInt64(a) * TInt64(b)` for products that overflow 32 bits.
- **`TTimeIntervalMicroSeconds32` is a 32-bit count of microseconds:** at most ~35 minutes. A
  timer for an hour (3 600 000 000 us) overflowed; use `RTimer::At` or repeat a shorter one.
- **`CActive::iStatus` is protected:** another class can't read an active object's result; add an
  accessor (`TInt Result() const { return iStatus.Int(); }`).
- **Keep a `TInetAddr` that `RSocket::Connect` gets in a member**, not a local, while the request
  is outstanding.
- **An implicit connection:** `RSocket::Open(ss, KAfInet, KSockStream, KProtocolInetTcp)` without
  an `RConnection` uses the phone's default connection (GnuBox sets its access point as the default
  with "don't ask"), and joins it if it's already up.
- **Test UIDs:** apps for one's own phone can use the unprotected range 0x01000000-0x0FFFFFFF
  (GnuBox 0x097764F0, NetTest 0x0A5D10A4).
