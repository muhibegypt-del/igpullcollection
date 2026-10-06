# Coverage and method

| Item | Count |
|---|---:|
| Original post folders | 504 |
| Original still images | 937 |
| Images OCR processed | 937 |
| Images with detected text | 911 |
| Original videos | 20 |
| Videos speech processed | 20 |
| Video frames OCR processed | 1629 |
| Video frames with detected text | 1531 |
| Repeated-text groups | 21 |
| Identical-media groups across posts | 2 |

## Method

- Still images: RapidOCR 3.9.2, original resolution. One record per image, including the extensionless JPEG.
- Videos: frames sampled at one frame per second and OCR'd with RapidOCR 3.9.2; frame lines below 0.85 confidence were omitted from the readable Markdown; English speech transcribed locally with faster-whisper base.en.
- Dates and captions are left unknown because the repository contains no corresponding metadata files.
- Theme labels are first-pass navigation aids from transparent keyword rules, not final editorial decisions.
- Repeated text is detected by exact normalization and high-similarity comparisons within shared opening phrases. Media duplication uses SHA-256.
- Raw OCR and speech output is preserved in [source-data](source-data/) with boxes, confidence scores, and timestamps.
- All original media folders remain unchanged. OCR and speech text may contain errors; see [review queue](REVIEW.md).
