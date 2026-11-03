# Tips from the Wikibooks Series 80 page

From the Maps 9300 notes (moved from `symbian-s80-build-tools/native9300/README.md`, 3 Nov 2026). Paths like `maps9300/` are the sibling repos in the same folder.

## 10. Tips from the Wikibooks Series 80 page

From [Symbian/S80](https://en.wikibooks.org/wiki/Symbian/S80) (Wikibooks, CC BY-SA); not yet checked here.

- **Key scan codes** (`TKeyEvent.iScanCode`) on the 9300 / 9500:

  | Key | Code | Key | Code |
  |---|---|---|---|
  | Joystick left / right / up / down / press | 170 / 171 / 172 / 173 / 174 | Arrows left / right / up / down | 14 / 15 / 16 / 17 |
  | Menu | 148 | Chr | 24 |
  | Ctrl | 22 | Left / right Shift | 18 / 19 |
  | Esc | 4 | Enter | 3 |
  | Backspace | 1 | Tab | 2 |
  | Space | 5 | Caps Lock | 26 |
  | Comma / dot | 121 / 122 | Minus / plus | 123 / 131 |
  | Letters a-z | 65-90 | Digits 0-9 | 48-57 |

  The joystick's own codes could replace the virtual mouse pointer that Maps 9300's 3D view reads it
  through.
- **Choosing the connection:** don't change `CCommsDbConnectionPrefTableView` from an app; pass a
  `TCommDbConnPref` to `RConnection::Start`. (GnuBox writes the preferences on purpose: setting the
  phone's default is its job.)
- **An app that won't start:** check overrides of `CEikAppUi::ProcessCommandParametersL` (its return
  value doesn't behave as on S60: `ETrue` differs) and of `ProcessMessageL`.
