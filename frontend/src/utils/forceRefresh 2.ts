// src/utils/forceRefresh.ts
export const forceRefresh = (url?: string) => {
  if (typeof window === 'undefined') return;
  
  // Clear browser cache for CSS
  const styleTags = document.querySelectorAll('link[rel="stylesheet"]');
  styleTags.forEach((tag: any) => {
    const href = tag.getAttribute('href');
    if (href && href.includes('_next/static/css')) {
      tag.setAttribute('href', `${href}?v=${Date.now()}`);
    }
  });
  
  // Reload the page
  if (url) {
    window.location.href = url;
  } else {
    window.location.reload();
  }
};