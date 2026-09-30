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

  _extractHierarchy(doc) {
    let courseName = '';
    let spaceName = null;
    let sectionName = null;
    let formattedTitle = '';

    // 1. Community Name extraction (e.g. "Tech Leads club")
    const ogSite = doc.querySelector('meta[property="og:site_name"]')?.getAttribute('content')?.trim();
    const appName = doc.querySelector('meta[name="application-name"]')?.getAttribute('content')?.trim();
    const logoAlt = doc
      .querySelector(
        'a[data-testid="community-logo"] img[alt], header a[href="/"] img[alt], .community-name, [data-testid="community-header"]'
      )
      ?.getAttribute('alt')
      ?.trim();

    const rawDocTitle = doc.title || '';
    const titleParts = rawDocTitle
      .split(/[|·–—]/)
      .map((p) => p.trim())
      .filter(Boolean);
    let titleSuffix = '';
    if (titleParts.length > 1) {
      titleSuffix = titleParts[titleParts.length - 1];
    }

    // 2. Space / Course Name extraction (e.g. "IA First Dev")
    // In Circle AI Shell, the course/space is in the header next to the sidebar toggle button
    const shellHeaderEl = doc.querySelector(
      '[data-testid="circle-ai-shell-sidebar-trigger"] ~ span, ' +
      '[data-testid="circle-ai-shell-sidebar-trigger"] + span, ' +
      'button[aria-label*="barra lateral"] ~ span, ' +
      'button[title*="barra lateral"] ~ span, ' +
      '.border-b .text-label-md.text-primary, ' +
      '[class*="h-12"] .text-label-md.text-primary, ' +
      '.space-name, [data-testid="space-title"]'
    );

    if (shellHeaderEl && this._isVisible(shellHeaderEl)) {
      const text = shellHeaderEl.innerText.trim();
      if (text && text.length > 1 && !text.toLowerCase().includes('concluir') && !text.toLowerCase().includes('favorito')) {
        spaceName = text;
      }
    }

    // 3. Breadcrumbs fallback
    const breadcrumbLinks = Array.from(
      doc.querySelectorAll('nav[aria-label="Breadcrumb"] a, nav[aria-label="Breadcrumb"] span, ol[aria-label="Breadcrumb"] li')
    )
      .map((el) => el.innerText.trim())
      .filter((t) => t && t !== '/' && t !== '>' && t !== '•');

    if (breadcrumbLinks.length >= 2) {
      courseName = breadcrumbLinks[0];
      if (!spaceName) spaceName = breadcrumbLinks[1];
    } else if (breadcrumbLinks.length === 1) {
      courseName = breadcrumbLinks[0];
    }

    if (!courseName) {
      courseName = ogSite || appName || logoAlt || titleSuffix || '';
    }

    // If doc.title has middle part (Lesson | Course | Community)
    if (!spaceName && titleParts.length >= 3) {
      spaceName = titleParts[titleParts.length - 2];
    }

    // Fallbacks and alignment
    if (!courseName || (spaceName && courseName.toLowerCase() === spaceName.toLowerCase())) {
      courseName = spaceName || 'Curso Online';
      spaceName = null;
    } else if (spaceName && courseName && spaceName.toLowerCase() === courseName.toLowerCase()) {
      spaceName = null;
    }

    // 2. Locate module cards in curriculum sidebar
    // Circle structure: <div class="flex flex-col rounded-md border border-primary">
    const moduleCards = Array.from(
      doc.querySelectorAll(
        '.rounded-md.border-primary, div[class*="rounded-md"][class*="border-primary"], div[class*="rounded-md border"]'
      )
    ).filter((card) => card.querySelector('.text-heading-sm, [class*="text-heading"]'));

    // 3. Locate active lesson element
    // In Circle, active lesson has bg-tertiary (or aria-current="page")
    let activeLessonEl =
      doc.querySelector('.bg-tertiary .text-label-sm') ||
      doc.querySelector('.bg-tertiary [id^="base-ui-"]') ||
      doc.querySelector('.bg-tertiary') ||
      doc.querySelector('[aria-current="page"] .text-label-sm') ||
      doc.querySelector('[aria-current="page"]') ||
      doc.querySelector('nav [data-active="true"]') ||
      doc.querySelector('[data-testid="active-lesson"]');

    let rawTitle = '';
    if (activeLessonEl) {
      const titleInside = activeLessonEl.querySelector?.('.text-label-sm, [id^="base-ui-"]');
      rawTitle = (titleInside || activeLessonEl).innerText.trim();
    }

    if (!rawTitle) {
      rawTitle = this._extractTitle(doc);
    }

    // Clean up trailing status texts like "Concluído" or "Aula" if captured
    rawTitle = rawTitle.replace(/\n.*$/, '').trim();

    // 4. Identify module index and lesson index
    if (moduleCards.length > 0) {
      let targetCard = null;
      let moduleIdx = -1;

      for (let i = 0; i < moduleCards.length; i++) {
        const card = moduleCards[i];
        if (activeLessonEl && card.contains(activeLessonEl)) {
          targetCard = card;
          moduleIdx = i + 1;
          break;
        }
        // Match by title text inside card
        const titlesInCard = Array.from(card.querySelectorAll('.text-label-sm, [id^="base-ui-"]')).map((el) =>
          el.innerText.trim()
        );
        if (rawTitle && titlesInCard.includes(rawTitle)) {
          targetCard = card;
          moduleIdx = i + 1;
          break;
        }
      }

      if (targetCard) {
        const rawSectionTitle =
          targetCard.querySelector('.text-heading-sm, [class*="text-heading"]')?.innerText.trim() || `Modulo ${moduleIdx}`;
        // Add zero-padded module number if not already numbered
        sectionName = /^\d+[\s.-]/.test(rawSectionTitle)
          ? rawSectionTitle
          : `${String(moduleIdx).padStart(2, '0')} - ${rawSectionTitle}`;

        // Find lesson index within this card
        const lessonElements = Array.from(targetCard.querySelectorAll('.text-label-sm, [id^="base-ui-"]')).filter(
          (el) => !el.closest('span.text-label-xs') && el.innerText.trim().length > 1
        );

        let lessonIdx = -1;
        for (let j = 0; j < lessonElements.length; j++) {
          const el = lessonElements[j];
          if (
            (activeLessonEl && (el === activeLessonEl || el.contains(activeLessonEl) || activeLessonEl.contains(el))) ||
            (rawTitle && el.innerText.trim() === rawTitle)
          ) {
            lessonIdx = j + 1;
            break;
          }
        }

        if (lessonIdx !== -1 && rawTitle) {
          formattedTitle = /^\d+[\s.-]/.test(rawTitle)
            ? rawTitle
            : `${String(lessonIdx).padStart(2, '0')}. ${rawTitle}`;
        }
      }
    }

    if (!formattedTitle) {
      formattedTitle = rawTitle || this._extractTitle(doc);
    }

    if (!courseName) {
      courseName = this._extractCourseName(doc);
    }

    return {
      course_name: courseName,
      space_name: spaceName,
      section_name: sectionName,
      title: formattedTitle,
    };
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
    const hierarchy = this._extractHierarchy(doc);
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
      course_name: hierarchy.course_name,
      space_name: hierarchy.space_name,
      section_name: hierarchy.section_name,
      title: hierarchy.title,
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
