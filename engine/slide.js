/**
 * engine/slide.js — コアエンジン層（編集不要）
 * キーボード操作 / クリックナビ / フルスクリーン / ビューポートスケーリング / PDF書き出し
 */
(() => {
  const slides = () => [...document.querySelectorAll('.slide')];
  let cur = 0;

  function show(n) {
    const all = slides();
    cur = Math.max(0, Math.min(n, all.length - 1));
    all.forEach((s, i) => s.classList.toggle('is-active', i === cur));
    const el = document.querySelector('.slide-counter');
    if (el) el.textContent =
      `${String(cur + 1).padStart(2, '0')} / ${String(all.length).padStart(2, '0')}`;
  }

  const next = () => show(cur + 1);
  const prev = () => show(cur - 1);

  // ── キーボード ──
  document.addEventListener('keydown', e => {
    if (['ArrowRight', 'ArrowDown', ' '].includes(e.key)) { e.preventDefault(); next(); }
    if (['ArrowLeft', 'ArrowUp'].includes(e.key))         { e.preventDefault(); prev(); }
    if (e.key === 'f' || e.key === 'F')                   { toggleFullscreen(); }
  });

  // ── デッキクリック（ナビUI除く）──
  document.querySelector('.deck')?.addEventListener('click', e => {
    if (e.target.closest('.slide-ui')) return;
    next();
  });

  // ── ナビボタン ──
  document.getElementById('btn-prev')?.addEventListener('click', prev);
  document.getElementById('btn-next')?.addEventListener('click', next);
  document.getElementById('btn-fs')?.addEventListener('click', toggleFullscreen);
  document.getElementById('btn-pdf')?.addEventListener('click', exportPDF);

  // ── フルスクリーン ──
  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen();
    }
  }

  // ── PDF書き出し ──
  function exportPDF() {
    const params = new URLSearchParams(window.location.search);
    const scale = parseFloat(params.get('print-scale')) || 100;

    if (scale !== 100) {
      const factor = scale / 100;
      const style = document.createElement('style');
      style.id = 'print-scale-override';
      style.textContent = `
        @media print {
          @page { size: ${254 * factor}mm ${142.875 * factor}mm; }
          .slide { transform: scale(${factor}); transform-origin: top left; }
        }
      `;
      document.head.appendChild(style);
      requestAnimationFrame(() => {
        window.print();
        const el = document.getElementById('print-scale-override');
        if (el) el.remove();
      });
    } else {
      window.print();
    }
  }

  // ── ビューポートに合わせてスケーリング ──
  function scaleDeck() {
    const deck = document.querySelector('.deck');
    if (!deck) return;
    const scale = Math.min(window.innerWidth / 1280, window.innerHeight / 720);
    deck.style.transform = `scale(${scale})`;
  }

  window.addEventListener('resize', scaleDeck);
  scaleDeck();
  show(0);
})();
