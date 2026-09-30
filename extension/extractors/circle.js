/**
 * course2brain - Circle.so Platform Extractor
 * Handles courses, communities, and lessons hosted on Circle.so.
 */

class CircleExtractor extends (typeof BaseExtractor !== 'undefined' ? BaseExtractor : class {}) {
  get platformId() {
    return 'circle';
  }

  get platformName() {
    return 'Circle.so';
  }

  canHandle(url, doc) {
    if (!url) return false;
    const isCircleDomain = url.includes('.circle.so') || url.includes('/c/');
    const hasCircleElements = !!doc.querySelector('media-theme, #compass-app-root, [data-testid="post-body"], [data-testid="lesson-body"]');
    return isCircleDomain || hasCircleElements;
  }

  _isVisible(el) {
    if (!el) return false;
    if (el.closest('.hidden') || el.closest('[hidden]')) return false;
    return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  }

  _extractCourseName(doc) {
    // 1. Check breadcrumbs or space header
    const breadcrumb = doc.querySelector('nav[aria-label="Breadcrumb"] a, .space-name, [data-testid="space-title"]');
    if (breadcrumb && this._isVisible(breadcrumb)) {
      const text = breadcrumb.innerText.trim();
      if (text && text.length > 2) return text;
    }

    // 2. Check title prefix before separator
    const rawTitle = doc.title || '';
    const parts = rawTitle.split(/[|·–—]/);
    if (parts.length > 1 && parts[parts.length - 1].trim()) {
      return parts[parts.length - 1].trim();
    }

    return 'Curso Online';
  }

  _extractTitle(doc) {
    let title = '';

    // Active lesson in sidebar
    const activeItem = doc.querySelector(
      '[aria-current="page"], nav [data-active="true"], [data-testid="active-lesson"], a.bg-hover'
    );
    if (activeItem && this._isVisible(activeItem)) {
      const text = activeItem.innerText.trim();
      if (text && !text.toLowerCase().includes('bloqueada')) {
        title = text;
      }
    }

    // Visible headings
    if (!title) {
      const headings = Array.from(doc.querySelectorAll('h1, h2, h3'));
      for (const h of headings) {
        if (this._isVisible(h)) {
          const text = h.innerText.trim();
          if (
            text &&
            !text.toLowerCase().includes('bloqueada') &&
            !text.toLowerCase().includes('participe do curso') &&
            text.length > 3
          ) {
            title = text;
            break;
          }
        }
      }
    }

    // Title fallback
    if (!title || title.toLowerCase().includes('bloqueada')) {
      const rawTitle = doc.title || '';
      const parts = rawTitle.split(/[|·–—]/);
      if (parts.length > 0 && parts[0].trim() && !parts[0].toLowerCase().includes('bloqueada')) {
        title = parts[0].trim();
      } else {
        title = 'Aula Sem Titulo';
      }
    }

    return title;
  }

  _extractMediaUrl(doc) {
    let mediaUrl = null;
    const mediaTheme = doc.querySelector('media-theme');
    if (mediaTheme) {
      mediaUrl = mediaTheme.getAttribute('downloadurl') || mediaTheme.getAttribute('src');
    }

    if (!mediaUrl) {
      const downloadLink = doc.querySelector('a.download-button, a[download]');
      if (downloadLink && downloadLink.href) {
        mediaUrl = downloadLink.href;
      }
    }

    if (!mediaUrl) {
      const videoEl = doc.querySelector('video');
      if (videoEl && videoEl.src && !videoEl.src.startsWith('blob:')) {
        mediaUrl = videoEl.src;
      }
    }

    return mediaUrl;
  }

  async _extractCaptions(doc) {
    let captionsText = '';
    const tracks = Array.from(doc.querySelectorAll('track'));

    // 1. Track element URLs (including blob: tracks created in memory)
    for (const track of tracks) {
      if (track.src) {
        try {
          const resp = await fetch(track.src);
          const txt = await resp.text();
          if (txt && (txt.includes('WEBVTT') || txt.length > 50)) {
            captionsText = txt;
            break;
          }
        } catch (e) {
          console.warn('[c2b] Failed to fetch track.src:', e);
        }
      }
    }

    // 2. Video element active text tracks
    if (!captionsText) {
      const videoEl = doc.querySelector('video');
      if (videoEl && videoEl.textTracks) {
        for (let i = 0; i < videoEl.textTracks.length; i++) {
          const tt = videoEl.textTracks[i];
          if (tt.cues && tt.cues.length > 0) {
            captionsText = Array.from(tt.cues)
              .map((c) => c.text)
              .join('\n');
            break;
          }
        }
      }
    }

    // 3. Transcript container elements
    if (!captionsText) {
      const transcriptEl = doc.querySelector(
        '[data-testid="transcript"], .transcript-container, .lesson-transcript, [data-testid="video-transcript"]'
      );
      if (transcriptEl && this._isVisible(transcriptEl)) {
        captionsText = transcriptEl.innerText.trim();
      }
    }

    return captionsText;
  }

  _extractLinks(doc, areaPrincipal, seenUrls) {
    const links = [];
    if (!areaPrincipal) return links;

    areaPrincipal.querySelectorAll('a[href]').forEach((a) => {
      if (!this._isVisible(a)) return;
      if (a.closest('header, nav, aside, media-theme, #compass-app-root, .border-b')) return;

      const href = a.href ? a.href.trim() : '';
      const texto = a.innerText.trim() || a.getAttribute('title') || href;

      const isCircleNav =
        href.includes('/sections/') ||
        href.includes('/lessons/') ||
        href.includes('/spaces/') ||
        href.includes('/feed') ||
        href.includes('downloadurl') ||
        href.endsWith('#') ||
        href.startsWith('javascript:');

      if (
        href &&
        !isCircleNav &&
        !seenUrls.has(href) &&
        href !== window.location.href &&
        href !== window.location.href + '/'
      ) {
        seenUrls.add(href);
        links.push({ texto: texto, url: href });
      }
    });

    return links;
  }

  _extractNotes(doc, areaPrincipal) {
    let notesText = '';
    const candidates = Array.from(
      doc.querySelectorAll(
        '.prose, .tiptap, .ProseMirror, [data-testid="post-body"], [data-testid="lesson-body"], article, [data-testid="rich-text"]'
      )
    ).filter((el) => this._isVisible(el) && !el.innerText.toLowerCase().includes('aula bloqueada'));

    if (candidates.length > 0) {
      const principal = candidates[0];
      const clone = principal.cloneNode(true);
      clone.querySelector('media-theme')?.remove();
      clone.querySelector('#compass-app-root')?.remove();
      clone.querySelectorAll('button, nav').forEach((b) => b.remove());

      clone.querySelectorAll('a[href]').forEach((a) => {
        const href = a.href;
        const texto = a.innerText.trim();
        if (href && texto && !href.startsWith('javascript:')) {
          a.replaceWith(` [${texto}](${href}) `);
        }
      });

      notesText = clone.innerText.trim();
    }

    if (!notesText && areaPrincipal) {
      const clone = areaPrincipal.cloneNode(true);
      clone.querySelector('#compass-app-root')?.remove();
      clone.querySelector('media-theme')?.remove();
      clone.querySelectorAll('.hidden, [hidden], button, svg, header, nav, aside').forEach((el) => el.remove());

      clone.querySelectorAll('a[href]').forEach((a) => {
        const href = a.href;
        const texto = a.innerText.trim();
        if (href && texto && !href.startsWith('javascript:')) {
          a.replaceWith(` [${texto}](${href}) `);
        }
      });

      const text = clone.innerText.trim();
      if (!text.toLowerCase().includes('aula bloqueada') && text.length > 30) {
        notesText = text;
      }
    }

    return notesText;
  }

  async extract(doc) {
    const courseName = this._extractCourseName(doc);
    const title = this._extractTitle(doc);
    const mediaUrl = this._extractMediaUrl(doc);
    const captionsText = await this._extractCaptions(doc);

    const areaPrincipal = doc.querySelector('main') || doc.body;
    const seenUrls = new Set();
    const links = this._extractLinks(doc, areaPrincipal, seenUrls);
    const notesText = this._extractNotes(doc, areaPrincipal);

    // Extract bare URLs from notes if any
    if (notesText) {
      const urlRegex = /(https?:\/\/[^\s<>"'{}|\\^`]+)/gi;
      let match;
      while ((match = urlRegex.exec(notesText)) !== null) {
        const rawUrl = match[1].replace(/[.,;:)]+$/, '');
        if (
          !seenUrls.has(rawUrl) &&
          !rawUrl.includes('/sections/') &&
          !rawUrl.includes('/lessons/') &&
          !rawUrl.includes('assets-v2.circle.so')
        ) {
          seenUrls.add(rawUrl);
          links.push({ texto: rawUrl, url: rawUrl });
        }
      }
    }

    return {
      platform: this.platformId,
      course_name: courseName,
      title: title,
      captions_text: captionsText,
      notes_text: notesText,
      links: links,
      page_url: window.location.href,
      media_url: mediaUrl,
    };
  }
}

// Self-register in browser context
if (typeof window !== 'undefined') {
  window.CircleExtractor = CircleExtractor;
  window.c2bExtractors = window.c2bExtractors || [];
  window.c2bExtractors.push(new CircleExtractor());
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { CircleExtractor };
}
