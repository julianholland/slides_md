---
layout: title
title: slide_maker Cheatsheet
subtitle: Minimal snippet per feature
date: today
---

+++

---
layout: stacked
kicker: Layout - title
title: title layout
---

...

```yaml
---
layout: title
title: My Presentation
subtitle: A subtitle
author: Jane Doe
date: today
background: images/hero.jpg
---
```

+++

---
layout: stacked
kicker: Layout - content
title: content layout (image)
---

...

```yaml
---
layout: content
title: Why This Matters
image: example-image
image_alt: A placeholder diagram
---
```

+++

---
layout: stacked
kicker: Layout - content
title: content layout (image pair)
---

...

```yaml
---
layout: content
title: Before vs After
images:
  - image: example-image-a
    alt: Before
  - image: example-image-b
    alt: After
---
```

+++

---
layout: stacked
kicker: Layout - stacked
title: stacked layout (formula)
---

...

```yaml
---
layout: stacked
title: The Core Equation
formula: E = mc^2
formula_note: Mass-energy equivalence
---
```

+++

---
layout: stacked
kicker: Layout - split
title: split layout
---

...

```yaml
---
layout: split
title: Two Approaches
panels:
  - image: example-image-a
    label: Before
  - image: example-image-b
    label: After
---
```

+++

---
layout: stacked
kicker: Layout - image
title: image layout
---

...

```yaml
---
layout: image
image: example-image
fit: cover
---
```

+++

---
layout: stacked
kicker: Background
title: background image + opacity
---

...

```yaml
---
layout: content
title: Dimmed Backdrop
background: example-image
background_opacity: 0.25
---
```

+++

---
layout: stacked
kicker: Images
title: placeholder images
---

...

```yaml
image: example-image-c
```

+++

---
layout: stacked
kicker: Comments
title: HTML-style comments
---

...

<code>&lt;!-- this text never reaches the build --&gt;</code>

+++

---
layout: stacked
kicker: KaTeX
title: inline vs block math
---

...

```text
inline: $q_{min}$
block:  formula: q_{min}
```

+++

---
layout: stacked
kicker: Themes
title: presets and overrides
---

...

Preset:

```yaml
theme: alomancy
```

Override:

```yaml
theme:
  accent: "#4cc9f0"
```

+++

---
layout: stacked
kicker: CLI
title: build flags
---

...

```bash
slide-maker build slides.md -o build/deck --pdf deck.pdf --thumbnail deck.png --strict --force
```
