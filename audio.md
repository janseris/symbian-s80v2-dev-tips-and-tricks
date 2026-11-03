# Audio on the Nokia 9300: what plays and what it costs

Measured on a Nokia 9300 by AudioProbe 1.0-1.3 (a native S80 test app from the GnuBox chat,
28 Oct 2026; the full report and raw logs: `phoneapk/test-results/audioprobe/`).

- **Players (MMF controllers):** Symbian Audio controller (.wav .au .raw), Real Video Player (.mp4
  .3gp .rm .amr .awb .mp3 ...), Advanced Audio controller (.amr .awb .aac .mp3), 3GP Audio
  controller (.3gp .m4a .mp4), MIDI and tone controllers.
- **CPU while playing** with `CMdaAudioPlayerUtility` (a counting thread's method):

  | Format | CPU |
  |---|---|
  | MP3 (32 and 128 kbit/s), AAC-LC 32 kbit/s (.aac ADTS, .m4a, .3gp) | ~0 % |
  | AMR-NB 4.75-12.2 kbit/s (.amr, .3gp) | 1-3 % |
  | IMA ADPCM WAV 8-22 kHz, PCM WAV 11/22 kHz, A-law, mu-law | 0-1 % |
  | GSM 6.10 WAV | 8 % (a software codec) |

  MP3 / AAC / AMR are decoded on the DSP, not the ARM: they cost the app almost nothing.
- **`CMdaAudioOutputStream`, PCM16 mono:** 8000-48000 Hz all play, at the right rate, 0-2 % CPU.
  `SetDataTypeL` accepts `' P16'` and `' AMR'`; P8, IMAD, ALAW, uLAW and GSM6 give KErrNotSupported.
- **Two players at once:** a second player (IMA WAV + AMR) made both stop with **KErrDied (-13)**;
  a PCM output stream kept playing next to them. For game sounds, mix yourself into one PCM stream.
- **A click at the start** of MP3 128 kbit/s, AAC .aac and AAC .m4a (not MP3 32k or AAC .3gp).
  AudioProbe 1.3 tries `SetVolumeRamp` (200 ms) and 0.3 s of silence + a 30 ms fade-in in the file.
- `CMMFDevSound::InitializeL` gave no callback within 5 s in that test (not looked into further).
- For lots of short sound / voice clips (e.g. game dialogue), IMA ADPCM at 11 kHz sounded fine
  and costs ~0 % CPU; AMR packs speech smaller still.
