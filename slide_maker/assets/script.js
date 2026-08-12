(function () {
  const slides = document.querySelectorAll(".slide");
  const total = slides.length;
  let current = 0;

  const counterCurrent = document.querySelector(".slide-counter .current");
  const counterTotal = document.querySelector(".slide-counter .total");
  counterTotal.textContent = total;

  function show(index) {
    current = Math.max(0, Math.min(total - 1, index));
    slides.forEach((slide, i) => slide.classList.toggle("active", i === current));
    counterCurrent.textContent = current + 1;
  }

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
