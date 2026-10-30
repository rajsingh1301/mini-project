# Backend API contract (what the frontend may rely on)

Owner: backend (`server.py`, `modules/`). The frontend only reads these fields.
Fields are only ever **added**, not renamed or removed, unless the frontend
has already stopped using them. Change this file first, then the code.

Never parse the spoken text to decide arrows, colours or vibration: use the
language-independent fields (`direction`, `alert`, `clear`, `kind`).

## Languages
`en`, `hi`. Unknown codes fall back to `en`. `GET /api/health` lists them in `languages`.
All spoken text in the replies below is already in the requested language.

## `GET /api/health`
```json
{"status": "ok", "model": "yolov8n.pt", "structure_model": true, "device": "mps", "languages": ["en", "hi"]}
```

## WebSocket `/ws?lang=hi` (Walk mode)
Client sends one JPEG (binary) and waits for the reply before sending the next.
Changing the language means opening a new connection with a different `lang`.

Reply (JSON):
| field | type | meaning |
|---|---|---|
| `width`, `height` | int | size of the frame the boxes refer to |
| `detections` | list | see below |
| `instruction` | string or null | phrase to speak now (null = say nothing) |
| `emergency` | bool | speak urgently, interrupt other speech |
| `alert` | `"stop"` / `"caution"` / null | urgency of `instruction` (vibration, banner colour) |
| `direction` | `"left"` / `"ahead"` / `"right"` / null | where the hazard is (arrow) |
| `clear` | bool | `instruction` is the "path clear" message |
| `latency_ms` | float | backend processing time |

Detection: `label` (English class name), `confidence` (0-1), `bbox` `[x1,y1,x2,y2]` in frame pixels,
`proximity` (`far`/`near`/`immediate`), `direction`, `approaching` (bool),
`stairs_dir` (`"up"` / `"down"` / null, stairs only, null when unsure).

Error reply: `{"error": "bad frame"}` (connection stays open).

## `POST /api/read` (Read mode)
Multipart form: `image` (JPEG, full resolution), `lang` (optional, default `en`).

Reply (JSON):
| field | type | meaning |
|---|---|---|
| `summary` | string | full explanation to speak |
| `text` | string | text found on the board, as written |
| `lines` | list of strings | the text, line by line |
| `kind` | string or null | sign type (`exit`, `no_entry`, `warning`, `stairs`, `traffic_light`, ...) |
| `hints` | list of strings | how to aim the camera, in the requested language |
| `error` | string (only on failure) | message to show/speak |

`POST /api/ocr` is a legacy alias that returns only `{"text": ...}`.
