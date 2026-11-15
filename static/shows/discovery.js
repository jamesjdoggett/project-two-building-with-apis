document.querySelectorAll('[data-poster]').forEach((poster) => {
  const fallback = () => {
    poster.removeEventListener('error', fallback);
    if (!poster.src.endsWith(poster.dataset.fallback)) {
      poster.src = poster.dataset.fallback;
    }
  };
  poster.addEventListener('error', fallback);
  if (poster.complete && poster.naturalWidth === 0) fallback();
});

const searchForm = document.querySelector('[data-search-form]');
if (searchForm) {
  const loading = searchForm.querySelector('[data-loading]');
  searchForm.addEventListener('submit', () => {
    searchForm.setAttribute('aria-busy', 'true');
    loading.classList.remove('hidden');
  });
  window.addEventListener('pageshow', () => {
    searchForm.removeAttribute('aria-busy');
    loading.classList.add('hidden');
  });
}
