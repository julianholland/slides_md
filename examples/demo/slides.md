---
layout: title
title: Slide Maker Demo
subtitle: A generated deck matching the sulfur_slides look and feel
author: Julian Holland
date: today
background: images/hero.jpg
---

+++

---
layout: content
kicker: Overview
title: Why a Markdown Slide Tool
image: images/diagram.png
image_alt: Diagram of the markdown-to-HTML pipeline
image_label: Figure 1. Build pipeline
image_reference: holland2024
---

- Author once in a single Markdown file [@holland2024]
  - YAML frontmatter per slide controls layout and media
- Generator assembles static HTML/CSS/JS
  - No client-side framework, matches the sulfur_slides look
<!-- TODO: add a bullet about deck.yaml theming here once it's finalized -->

> Blockquotes render as an italic grey callout, matching the KaTeX formula box style

+++

---
layout: content
kicker: Feature
title: Multiple Images
images:
  - image: images/screenshot_a.png
    alt: First screenshot
    label: Before
  - image: images/screenshot_b.png
    alt: Second screenshot
    label: After
---

- Two images auto-arrange from their aspect ratio
- Wide images stack on top of each other; narrow ones sit side by side

+++

---
layout: content
kicker: Feature
title: Placeholder Images
image: example-image-c
---

- No file needed while drafting — just write `example-image-a` .. `example-image-z`
- Renders a lettered placeholder box, auto-copied into the build

+++

---
layout: content
kicker: Feature
title: Phase-In Reveal
phase_in: true
phase_images:
  - image: example-image-a
  - image: example-image-b
---

- Bullets reveal one at a time, dimming as new ones appear
- The image advances alongside, freezing on the last once exhausted

+++

<!--
A whole slide can be commented out too — this draft never reaches the build:

+++

---
layout: content
title: Draft slide, not ready yet
---

- Not finished
-->

+++

---
layout: content
kicker: Feature
title: Background Images with Alpha
background: images/watermark.png
background_opacity: 0.25
---

- Any slide can have a translucent background image
- Controlled per-slide via `background_opacity`
- Independent of the title slide's translucent panel

+++

---
layout: image
image: images/watermark.png
image_alt: A full-bleed photo used as the entire slide
kicker: Feature
title: Full-Bleed Image Slide
---

+++

---
layout: stacked
kicker: Math
title: KaTeX Support
formula: E = \int_{q_{min}}^{q_{max}} S(q)\, dq
formula_note: Rendered client-side with vendored KaTeX (no CDN)
---

- Inline math like $S(q)$ works directly in bullet text
- Block equations use the dedicated `formula` field

+++

---
layout: split
kicker: Comparison
title: Split Panel Layout
panels:
  - image: images/before.png
    label: Before
  - image: images/after.png
    label: After
---

+++

---
layout: references
title: References
---
