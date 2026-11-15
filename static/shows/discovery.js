function fallbackPoster(poster) {
  if (poster.matches('[data-poster]') && !poster.src.endsWith(poster.dataset.fallback)) {
    poster.src = poster.dataset.fallback;
  }
}
document.addEventListener('error', (event) => {
  if (event.target instanceof HTMLImageElement) fallbackPoster(event.target);
}, true);
function checkPosters() {
  document.querySelectorAll('[data-poster]').forEach((poster) => {
    if (poster.complete && poster.naturalWidth === 0) fallbackPoster(poster);
  });
}
checkPosters();
document.addEventListener('htmx:afterSwap', checkPosters);
document.addEventListener('submit', (event) => {
  const form = event.target.closest('[data-search-form]');
  if (form && !window.htmx) {
    form.setAttribute('aria-busy', 'true');
    document.querySelector('#discover-loading').classList.add('htmx-request');
  }
});
window.addEventListener('pageshow', () => {
  document.querySelectorAll('[aria-busy]').forEach((el) => el.removeAttribute('aria-busy'));
  document.querySelectorAll('.htmx-request').forEach((el) => el.classList.remove('htmx-request'));
});
document.addEventListener('htmx:beforeRequest', (event) => {
  const panel = event.detail.elt.closest('section');
  if (panel) {
    panel.setAttribute('aria-busy', 'true');
    panel.querySelector('.request-error').hidden = true;
  }
});
document.addEventListener('htmx:afterRequest', (event) => {
  const panel = event.detail.elt.closest('section');
  if (panel) {
    panel.removeAttribute('aria-busy');
    if (event.detail.failed) panel.querySelector('.request-error').hidden = false;
  }
});
