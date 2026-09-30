/**
 * course2brain - Base Extractor Interface
 * All platform extractors must extend BaseExtractor and register themselves in window.c2bExtractors.
 */
class BaseExtractor {
  /**
   * Unique identifier for the platform (e.g. 'circle', 'skool', 'hotmart').
   * @returns {string}
   */
  get platformId() {
    return 'base';
  }

  /**
   * Human-readable name for the platform.
   * @returns {string}
   */
  get platformName() {
    return 'Base Platform';
  }

  /**
   * Checks whether this extractor can handle the current page.
   * @param {string} url - Current page URL.
   * @param {Document} doc - DOM Document.
   * @returns {boolean}
   */
  canHandle(url, doc) {
    return false;
  }

  /**
   * Extracts normalized lesson payload from the page DOM.
   *
   * Returned payload schema:
   * {
   *   platform: string,
   *   course_name: string,
   *   title: string,
   *   captions_text: string,
   *   notes_text: string,
   *   links: Array<{ texto: string, url: string }>,
   *   page_url: string,
   *   media_url: string | null
   * }
   *
   * @param {Document} doc - DOM Document.
   * @returns {Promise<Object>}
   */
  async extract(doc) {
    throw new Error('extract() must be implemented by concrete extractor subclass');
  }
}

// Global registry for available extractors
if (typeof window !== 'undefined') {
  window.BaseExtractor = BaseExtractor;
  window.c2bExtractors = window.c2bExtractors || [];
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { BaseExtractor };
}
