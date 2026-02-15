# 🚀 CONTINUE HERE: ∑VAL Project Context

## 📍 Project Location
**Path:** `/Users/siddharthbellad/SIDPROJECTS/SCAI-Hackathon-2026`
**Web App:** `/Users/siddharthbellad/SIDPROJECTS/SCAI-Hackathon-2026/web`

## 🛠️ Current State: "ASCII Brutalist" Redesign (V2)
We have just finished implementing the V2 redesign of the homepage.

**Completed:**
- ✅ **Design System:** Pure white text (`#ffffff`), Amber Gold accent (`#e8b84b`), JetBrains Mono + Cormorant Garamond fonts.
- ✅ **Layout:** Tighter spacing, two-column hero (Text Left / Art Right).
- ✅ **Components:**
  - `AsciiParticles.js`: Canvas-based floating ASCII background.
  - `LadyJustice.js`: Component wired to display `/lady-justice.png`.
- ✅ **Pages:** Leaderboard, Reliability, and Methodology pages are fully styled.

## 🚧 IMMEDIATE ACTION REQUIRED
The **Lady Justice** image was generated but could not be automatically copied to the public folder due to workspace restrictions.

**You must run this command manually to fix the missing image:**
```bash
cp /Users/siddharthbellad/.gemini/antigravity/brain/2ade3960-5334-4195-b1ab-f6e08dae963e/lady_justice_gold_1771090130276.png /Users/siddharthbellad/SIDPROJECTS/SCAI-Hackathon-2026/web/public/lady-justice.png
```

## 📝 Design Specs for Next AI
If you are moving to a new session, provide this context:

**Aesthetic:** "High-fidelity ASCII Brutalism"
- **Background:** `#0a0a0a` (Near Black)
- **Text:** `#ffffff` (Primary), `#c0bdb5` (Secondary)
- **Accent:** `#e8b84b` (Amber/Gold) - Used for emphasis and active states only.
- **UI Elements:**
  - No border-radius (0px).
  - Dashed lines (`1px dashed #40403a`) for separation.
  - Pipe separators (`|`) in lists.
  - ASCII progress bars: `████████░░`

## 📂 Key Files
- `web/app/globals.css`: Contains all CSS variables and base styles.
- `web/app/page.js`: Homepage layout implementation.
- `web/app/components/LadyJustice.js`: Hero image component.
- `web/app/components/AsciiParticles.js`: Background animation.

## 🏃‍♂️ How to Run
```bash
cd web
npm run dev
```
