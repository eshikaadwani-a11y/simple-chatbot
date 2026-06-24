# Portfolio assets

This folder holds the visual assets used in the README and portfolio.

## Included now
- **`architecture.svg`** — the system architecture diagram (renders directly on
  GitHub and in the README). SVG is preferred over PNG: it's crisp at any zoom,
  diff-able in git, and editable as text.

  To export a PNG (e.g. for slides), open the SVG in a browser and "Save as image",
  or use a CLI:
  ```bash
  # Option A: rsvg-convert
  rsvg-convert docs/assets/architecture.svg -o docs/assets/architecture.png
  # Option B: Inkscape
  inkscape docs/assets/architecture.svg --export-type=png --export-filename=docs/assets/architecture.png
  ```

## Screenshots — capture these locally
Screenshots require the app to be running, so they are **not** committed here yet
(they can't be generated in CI). Capture them once you run the stack and drop the
files in this folder with the names below; the README already references them.

| File | Page | How to capture |
|---|---|---|
| `landing.png` | `/` | Run `npm run dev`, open `http://localhost:3000` |
| `chat.png` | `/chat` | Sign in, ask the agent something; capture mid-stream to show the agent/tool indicators |
| `dashboard.png` | `/dashboard` | Complete a topic / take a quiz so XP, streak, and charts populate |
| `resume.png` | `/resume` | Upload a sample PDF to show the ATS score ring + rewrites |

### Tips for clean screenshots
- Use a viewport around **1440×900** and a clean browser window (no bookmarks bar).
- For the chat, capture a moment where the “🧠 Agent / 🔧 tool” chips are visible.
- For the resume page, use a real (non-sensitive) sample resume so the ATS ring and
  bullet rewrites are populated.
- Optimize before committing: `pngquant` or `squoosh` keeps the repo light.

> Once added, reference them in `README.md`, e.g.
> `![Dashboard](docs/assets/dashboard.png)`.
