# Layout Gallery

A live, click/keyboard-navigable example of each of slide_maker's five layouts, built
from real figures pulled from an actual research talk (with the talk's own narrative text
replaced by placeholder copy — the images and the one LaTeX formula below are genuine,
reused as-is). These decks are rebuilt from source every time these docs are built, so
they always reflect the current templates/CSS, not a stale screenshot.

```{raw} html
<p><a href="_static/demo/full/index.html">Open the full 7-slide demo deck ↗</a></p>
```

The full deck always opens on slide 1 — there's no URL/hash routing in `assets/script.js`,
so use arrow keys or click the left/right edges to navigate once it's open. That's also
why each layout gets its own single-purpose mini-deck below, rather than trying to deep
link into the combined one.

## Title

Centered title over a full-bleed background image, in a translucent panel.

```yaml
---
layout: title
title: Lorem Ipsum Dolor Sit Amet
subtitle: Consectetur adipiscing elit sed do eiusmod
background: lj_strucures.png
background_opacity: 0.5
---
```

```{raw} html
<iframe class="demo-iframe" src="_static/demo/title/index.html" loading="lazy"></iframe>
```

## Content

`title`/`kicker` + bullets on the left, media on the right — a single boxed `image`, or a
two-image `images` pair auto-arranged from real pixel aspect ratio.

```markdown
---
layout: content
kicker: Lorem Ipsum
title: Dolor Sit Amet Consectetur
image: acs_c_to_s_electron_transfer.png
image_alt: Lorem ipsum dolor sit amet consectetur adipiscing elit
image_label: Figure 1. Lorem ipsum
---

- Lorem ipsum dolor sit amet, consectetur adipiscing elit
- Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua
- Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris

+++

---
layout: content
kicker: Lorem Ipsum
title: Ut Labore Et Dolore Magna
images:
  - image: s_int_band_gap_bar.png
    alt: Lorem ipsum dolor sit amet
    label: Lorem ipsum
  - image: new_s_int_band_gap_bar.png
    alt: Consectetur adipiscing elit
    label: Dolor sit amet
---

- Duis aute irure dolor in reprehenderit in voluptate velit esse
- Excepteur sint occaecat cupidatat non proident sunt in culpa
```

```{raw} html
<iframe class="demo-iframe" src="_static/demo/content/index.html" loading="lazy"></iframe>
```

## Stacked

`title`/`kicker` + full-width bullets, no media column — also where block math
(`formula`) usually goes, since it gets the full slide width.

```markdown
---
layout: stacked
kicker: Lorem Ipsum
title: Sed Do Eiusmod Tempor
---

> Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua, ut enim ad minim veniam.

+++

---
layout: stacked
kicker: Lorem Ipsum
title: Formula Example
formula: E_{f} = \frac{E_{aC-O}}{N} - \left(1-\frac{n_O}{N}\right)E_{aC} - \frac{n_O}{N}E_{O}
formula_note: Lorem ipsum dolor sit amet consectetur adipiscing elit
---

- Lorem ipsum dolor sit amet
- Consectetur adipiscing elit sed do eiusmod
- Tempor incididunt ut labore et dolore magna aliqua
```

```{raw} html
<iframe class="demo-iframe" src="_static/demo/stacked/index.html" loading="lazy"></iframe>
```

## Split

`title`/`kicker` + a full-width row of 2-3 `panels` (image + caption), no bullets — good
for side-by-side comparisons.

```yaml
---
layout: split
kicker: Lorem Ipsum
title: Split Panel Layout Example
panels:
  - image: updated_bands_S8_on_g_C336S8.png
    label: Lorem Ipsum
    alt: Lorem ipsum dolor sit amet consectetur
  - image: updated_bands_S8_on_g_C32S8.png
    label: Dolor Sit Amet
    alt: Consectetur adipiscing elit sed do eiusmod
---
```

```{raw} html
<iframe class="demo-iframe" src="_static/demo/split/index.html" loading="lazy"></iframe>
```

## Image

A single `image` fills the entire slide edge-to-edge; `title`/`kicker` are optional,
shown as a small overlay caption panel when set.

```yaml
---
layout: image
image: lj_pareto_with_density.png
image_alt: Lorem ipsum dolor sit amet consectetur adipiscing elit
kicker: Lorem Ipsum
title: Full-Bleed Image Example
---
```

```{raw} html
<iframe class="demo-iframe" src="_static/demo/image/index.html" loading="lazy"></iframe>
```
