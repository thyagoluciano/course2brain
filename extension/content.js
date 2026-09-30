/**
 * course2brain - Content Script Dispatcher
 * Coordinates registered extractors and handles extension messages.
 */

function getActiveExtractor() {
  const extractors = window.c2bExtractors || [];
  const currentUrl = window.location.href;

  for (const ext of extractors) {
    try {
      if (ext.canHandle(currentUrl, document)) {
        return ext;
      }
    } catch (e) {
      console.warn('[c2b] Error evaluating extractor', ext.platformId, e);
    }
  }

  // Fallback generic extractor
  return {
    platformId: 'generic',
    platformName: 'Generic Web Page',
    canHandle: () => true,
    extract: async (doc) => {
      const title = doc.querySelector('h1')?.innerText?.trim() || doc.title || 'Aula Sem Titulo';
      const mainEl = doc.querySelector('main, article, #content') || doc.body;
      const notes = mainEl ? mainEl.innerText.slice(0, 5000) : '';

      return {
        platform: 'generic',
        course_name: 'Curso Web',
        title: title,
        captions_text: '',
        notes_text: notes,
        links: [],
        page_url: window.location.href,
        media_url: null,
      };
    }
  };
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  const extractor = getActiveExtractor();

  if (request.action === 'check_platform') {
    sendResponse({
      supported: extractor.platformId !== 'generic',
      platformId: extractor.platformId,
      platformName: extractor.platformName,
      url: window.location.href,
    });
    return true;
  }

  if (request.action === 'extract_lesson' || request.action === 'extrair_aula') {
    extractor
      .extract(document)
      .then((payload) => {
        console.log('[c2b] Extracted payload:', payload);
        sendResponse(payload);
      })
      .catch((err) => {
        console.error('[c2b] Extraction error:', err);
        sendResponse({ error: err.message || 'Erro durante extração do conteúdo' });
      });
    return true; // Keep message channel open for async response
  }
});
