(function () {
  const slides = document.querySelectorAll(".slide");
  const total = slides.length;
  let current = 0;

  const counterCurrent = document.querySelector(".slide-counter .current");
  const counterTotal = document.querySelector(".slide-counter .total");
  // A phase-in slide expands into several physical `.slide` elements that all share
  // one `data-display-index` — the counter shows that shared number, not raw DOM
  // position, so it stays put across a slide's reveal steps.
  counterTotal.textContent = new Set([...slides].map((s) => s.dataset.displayIndex)).size;

  // The footnote list is absolutely positioned in the slide's bottom-left corner, so
  // it doesn't push the body text out of its way -- if a slide's own bullet/body
  // content is tall enough to reach that corner (long bullets, many phase-in steps
  // accumulated, etc.), shrink the footnote text until it no longer overlaps rather
  // than let the two visually collide. Only .text-col (content layout) or
  // .slide-body.stacked (stacked layout) count as "the main text" here; other
  // layouts either have no such column or no bullets to overlap in the first place.
  const MIN_FOOTNOTE_REM = 0.6;
  const FOOTNOTE_STEP_REM = 0.05;

  function rectsOverlap(a, b) {
    return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
  }

  function fitFootnote(slide) {
    const footnote = slide.querySelector(".citation-footnotes");
    if (!footnote) return;
    footnote.style.fontSize = "";
    const textEl = slide.querySelector(".text-col") || slide.querySelector(".slide-body.stacked");
    if (!textEl) return;
    let size = 1;
    while (rectsOverlap(textEl.getBoundingClientRect(), footnote.getBoundingClientRect()) && size > MIN_FOOTNOTE_REM) {
      size -= FOOTNOTE_STEP_REM;
      footnote.style.fontSize = `${size}rem`;
    }
  }

  function show(index) {
    current = Math.max(0, Math.min(total - 1, index));
    slides.forEach((slide, i) => slide.classList.toggle("active", i === current));
    counterCurrent.textContent = slides[current].dataset.displayIndex;
    fitFootnote(slides[current]);
  }

  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => fitFootnote(slides[current]), 100);
  });

  function next() {
    show(current + 1);
  }

  function prev() {
    show(current - 1);
  }

  const lightbox = document.getElementById("lightbox");
  const lightboxImg = lightbox.querySelector("img");
  const MAX_ZOOM = 4;
  let zoomScale = 1;

  function originFromEvent(e) {
    const rect = lightboxImg.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    return [Math.min(100, Math.max(0, x)), Math.min(100, Math.max(0, y))];
  }

  function setZoom(scale, originX, originY) {
    zoomScale = Math.min(MAX_ZOOM, Math.max(1, scale));
    if (originX !== undefined) {
      lightboxImg.style.transformOrigin = `${originX}% ${originY}%`;
    }
    lightboxImg.style.transform = zoomScale === 1 ? "" : `scale(${zoomScale})`;
    lightboxImg.classList.toggle("zoomed", zoomScale > 1);
  }

  function openLightbox(img) {
    lightboxImg.src = img.currentSrc || img.src;
    lightboxImg.alt = img.alt;
    setZoom(1);
    lightbox.classList.add("active");
  }

  function closeLightbox() {
    lightbox.classList.remove("active");
    lightboxImg.src = "";
    setZoom(1);
  }

  document.querySelectorAll(".slide-content img").forEach((img) => {
    img.addEventListener("click", (e) => {
      e.stopPropagation();
      openLightbox(img);
    });
  });

  lightbox.addEventListener("click", closeLightbox);

  lightboxImg.addEventListener("click", (e) => {
    e.stopPropagation();
    if (zoomScale === 1) {
      const [ox, oy] = originFromEvent(e);
      setZoom(2, ox, oy);
    } else {
      setZoom(1);
    }
  });

  lightbox.addEventListener(
    "wheel",
    (e) => {
      if (!lightbox.classList.contains("active")) return;
      e.preventDefault();
      const [ox, oy] = originFromEvent(e);
      setZoom(zoomScale + (e.deltaY < 0 ? 0.3 : -0.3), ox, oy);
    },
    { passive: false }
  );

  document.addEventListener("keydown", (e) => {
    if (lightbox.classList.contains("active")) {
      if (e.key === "Escape") closeLightbox();
      return;
    }
    if (e.key === "ArrowRight" || e.key === " " || e.key === "PageDown") {
      next();
    } else if (e.key === "ArrowLeft" || e.key === "PageUp") {
      prev();
    }
  });

  document.querySelector(".nav-zone.prev").addEventListener("click", prev);
  document.querySelector(".nav-zone.next").addEventListener("click", next);

  show(0);

  if (window.renderMathInElement) {
    renderMathInElement(document.body, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
      ],
    });
  }
})();
