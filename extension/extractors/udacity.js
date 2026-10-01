/**
 * course2brain - Udacity Platform Extractor
 * Handles courses, nanodegrees, lessons, and video content hosted on Udacity.
 */

class UdacityExtractor extends (typeof BaseExtractor !== 'undefined' ? BaseExtractor : class {}) {
  get platformId() {
    return 'udacity';
  }

  get platformName() {
    return 'Udacity';
  }

  canHandle(url, doc) {
    if (!url) return false;
    const isUdacityDomain =
      url.includes('udacity.com') ||
      url.includes('classroom.udacity.com') ||
      url.includes('learn.udacity.com');

    const hasUdacityElements = !!doc.querySelector(
      '.program-title, [data-testid="youtube-player"], [data-woolf-resource], .lesson-content-scroll-container, youtube-video, button[aria-label*="Transcrição"]'
    );

    return isUdacityDomain || hasUdacityElements;
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

    // 1. Program / Course Title (e.g. "AI Engineering with Claude")
    const titleP = doc.querySelector('.program-title p, .program-title .chakra-text, [class*="program-title"] p');
    if (titleP && this._isVisible(titleP)) {
      const text = titleP.innerText.trim();
      if (text && text.length > 2) courseName = text;
    }

    if (!courseName) {
      const programContainer = doc.querySelector('.program-title, [class*="program-title"]');
      if (programContainer) {
        const clone = programContainer.cloneNode(true);
        clone.querySelectorAll('[role="progressbar"], [id*="progress"], span').forEach((el) => el.remove());
        const text = clone.innerText.trim().replace(/\n.*$/, '').trim();
        if (text && text.length > 2) courseName = text;
      }
    }

    if (!courseName) {
      const ogTitle = doc.querySelector('meta[property="og:title"]')?.getAttribute('content')?.trim();
      if (ogTitle && ogTitle.includes('|')) {
        courseName = ogTitle.split('|').pop().trim();
      } else {
        const rawTitle = doc.title || '';
        courseName = rawTitle.includes('|') ? rawTitle.split('|').pop().trim() : 'Curso Udacity';
      }
    }

    // 2. Part / Módulo Maior (e.g. "01 - Harness Engineering with Claude and Claude Code")
    const partContainer = doc.querySelector('.part-selector, [class*="part-selector"]');
    if (partContainer) {
      const partNameEl = partContainer.querySelector('button p:first-of-type, p.css-a5ozc8, button p');
      const rawPartName = partNameEl ? partNameEl.innerText.trim() : '';

      // Check fraction e.g. "1/4"
      const partFractionEl = partContainer.querySelector('p.css-90qrf4, .css-axw7ok p');
      const fractionText = partFractionEl ? partFractionEl.innerText.trim() : '';
      const fractionMatch = fractionText.match(/^(\d+)\s*\/\s*(\d+)/);

      let partNum = '';
      if (fractionMatch) {
        partNum = String(parseInt(fractionMatch[1], 10)).padStart(2, '0');
      }

      if (rawPartName) {
        if (partNum && !/^\d+[\s.-]/.test(rawPartName)) {
          spaceName = `${partNum} - ${rawPartName}`;
        } else {
          spaceName = rawPartName;
        }
      }
    }

    // 3. Raw main title from DOM as reference
    const mainHeading = doc.querySelector('main h1.chakra-text, main h1, .css-u8lxk4 h1, h1.chakra-text');
    const rawMainTitle = mainHeading && this._isVisible(mainHeading) ? mainHeading.innerText.trim() : '';

    // 4. Topic / Lesson and Concept / Subtopic from navigation accordion (ol[aria-label="Lições"] or .css-1khhvj9)
    const lessonsList = doc.querySelector('ol[aria-label*="Liç"], ol[aria-label="Lições"], ol.css-1khhvj9, [class*="css-1khhvj9"]');
    if (lessonsList) {
      const lessonItems = Array.from(lessonsList.querySelectorAll(':scope > li, li.css-qqfgvy'));

      let matchedLesson = null;
      let matchedLessonIdx = -1;
      let matchedConcept = null;
      let matchedConceptIdx = -1;

      for (let i = 0; i < lessonItems.length; i++) {
        const item = lessonItems[i];
        const concepts = Array.from(
          item.querySelectorAll('ul[aria-label*="Conceitos"] > li, ul[role="list"] > li, .chakra-accordion__panel li')
        );

        // Check for data-active="true"
        let activeEl = concepts.find((c) => c.getAttribute('data-active') === 'true');

        // Or match concept text against rawMainTitle
        if (!activeEl && rawMainTitle && concepts.length > 0) {
          activeEl = concepts.find((c) => {
            const p = c.querySelector('p.chakra-text, p');
            const txt = (p || c).innerText.trim();
            return txt.toLowerCase() === rawMainTitle.toLowerCase();
          });
        }

        if (activeEl) {
          matchedLesson = item;
          matchedLessonIdx = i + 1;
          matchedConcept = activeEl;
          matchedConceptIdx = concepts.indexOf(activeEl) + 1;
          break;
        }
      }

      if (matchedLesson) {
        // Extract Lesson Number
        const numEl = matchedLesson.querySelector('.css-1vd9frn, [class*="css-1vd9frn"]');
        const lessonNum = numEl ? parseInt(numEl.innerText.trim(), 10) : matchedLessonIdx;
        const paddedLessonNum = String(lessonNum || matchedLessonIdx).padStart(2, '0');

        // Extract Lesson Title
        const titleSpan = matchedLesson.querySelector(
          'span[id^="progress-"], span.css-1unrz39, button.chakra-accordion__button span'
        );
        const rawLessonTitle = titleSpan ? titleSpan.innerText.trim() : `Lição ${matchedLessonIdx}`;
        sectionName = /^\d+[\s.-]/.test(rawLessonTitle) ? rawLessonTitle : `${paddedLessonNum} - ${rawLessonTitle}`;

        // Extract Concept Title and Number
        if (matchedConcept) {
          const conceptP = matchedConcept.querySelector('p.chakra-text, p');
          let rawConceptTitle = (conceptP || matchedConcept).innerText.trim();
          // Remove status text if present (e.g. "Conceito foi concluído.")
          rawConceptTitle = rawConceptTitle.replace(/Conceito.*concluído\./gi, '').trim();

          const paddedConceptNum = String(matchedConceptIdx).padStart(2, '0');
          formattedTitle = /^\d+[\s.-]/.test(rawConceptTitle)
            ? rawConceptTitle
            : `${paddedConceptNum}. ${rawConceptTitle}`;
        }
      }
    }

    // 5. Fallbacks if sidebar not rendered or active item not matched
    if (!formattedTitle) {
      formattedTitle = rawMainTitle || (doc.title ? doc.title.split('|')[0].trim() : 'Aula Udacity Sem Titulo');
    }

    return {
      course_name: courseName,
      space_name: spaceName,
      section_name: sectionName,
      title: formattedTitle,
    };
  }

  _htmlToMarkdown(element) {
    if (!element) return '';
    const clone = element.cloneNode(true);

    // Remove buttons, svgs, feedback controls, sidebars
    clone
      .querySelectorAll('button, svg, [role="progressbar"], .chakra-button, [aria-label*="Feedback"]')
      .forEach((el) => el.remove());

    // Convert headings
    clone.querySelectorAll('h1').forEach((h) => h.replaceWith(`\n# ${h.innerText.trim()}\n`));
    clone.querySelectorAll('h2').forEach((h) => h.replaceWith(`\n## ${h.innerText.trim()}\n`));
    clone.querySelectorAll('h3').forEach((h) => h.replaceWith(`\n### ${h.innerText.trim()}\n`));
    clone.querySelectorAll('h4').forEach((h) => h.replaceWith(`\n#### ${h.innerText.trim()}\n`));

    // Convert list items
    clone.querySelectorAll('li').forEach((li) => {
      li.replaceWith(`\n- ${li.innerText.trim()}`);
    });

    // Convert code blocks
    clone.querySelectorAll('pre code, pre').forEach((pre) => {
      const code = pre.innerText.trim();
      pre.replaceWith(`\n\`\`\`\n${code}\n\`\`\`\n`);
    });

    // Convert inline code
    clone.querySelectorAll('code').forEach((c) => {
      c.replaceWith(` \`${c.innerText.trim()}\` `);
    });

    // Convert bold and italic
    clone.querySelectorAll('strong, b').forEach((b) => {
      b.replaceWith(`**${b.innerText.trim()}**`);
    });
    clone.querySelectorAll('em, i').forEach((i) => {
      i.replaceWith(`*${i.innerText.trim()}*`);
    });

    // Convert links
    clone.querySelectorAll('a[href]').forEach((a) => {
      const href = a.href;
      const text = a.innerText.trim() || href;
      if (href && !href.startsWith('javascript:')) {
        a.replaceWith(` [${text}](${href}) `);
      }
    });

    // Convert paragraphs
    clone.querySelectorAll('p').forEach((p) => {
      p.replaceWith(`\n\n${p.innerText.trim()}\n\n`);
    });

    let text = clone.innerText || '';
    // Normalize excessive newlines
    text = text.replace(/\n{3,}/g, '\n\n').trim();
    return text;
  }

  _extractNotes(doc, mainEl) {
    let notes = '';

    // Look for Udacity's markdown containers (.ureact-markdown)
    const markdownContainers = Array.from(
      doc.querySelectorAll('.ureact-markdown, [data-woolf-resource] .ureact-markdown')
    ).filter((el) => this._isVisible(el));

    if (markdownContainers.length > 0) {
      const chunks = markdownContainers.map((container) => this._htmlToMarkdown(container));
      notes = chunks.filter(Boolean).join('\n\n---\n\n');
    }

    if (!notes && mainEl) {
      // Fallback to content scroll container
      const scrollContainer = doc.querySelector('.lesson-content-scroll-container') || mainEl;
      notes = this._htmlToMarkdown(scrollContainer);
    }

    return notes;
  }

  _normalizeYouTubeUrl(url) {
    if (!url) return null;
    try {
      const parsed = new URL(url);
      let videoId = null;

      if (parsed.hostname.includes('youtube.com')) {
        if (parsed.pathname === '/watch') {
          videoId = parsed.searchParams.get('v');
        } else if (parsed.pathname.startsWith('/embed/')) {
          videoId = parsed.pathname.replace('/embed/', '').split('?')[0];
        }
      } else if (parsed.hostname.includes('youtu.be')) {
        videoId = parsed.pathname.replace('/', '').split('?')[0];
      }

      if (videoId) {
        return `https://www.youtube.com/watch?v=${videoId}`;
      }
    } catch (e) {
      // Return raw url if parsing fails
    }
    return url;
  }

  async _extractMediaUrl(doc) {
    let mediaUrl = null;

    // 1. Check if <youtube-video> component already exists in DOM
    const ytVideoEl = doc.querySelector('youtube-video');
    if (ytVideoEl && ytVideoEl.getAttribute('src')) {
      mediaUrl = ytVideoEl.getAttribute('src');
    }

    // 2. Check for YouTube iframe
    if (!mediaUrl) {
      const iframe = doc.querySelector(
        'iframe[src*="youtube.com/embed"], iframe[src*="youtube.com"], iframe[src*="youtu.be"]'
      );
      if (iframe && iframe.src) {
        mediaUrl = iframe.src;
      }
    }

    // 3. If video player is in preview mode (.react-player__preview), trigger play to mount YouTube video
    if (!mediaUrl) {
      const previewEl = doc.querySelector(
        '.react-player__preview, [data-testid="youtube-player"] .react-player__preview, .react-player__play-icon'
      );
      if (previewEl && this._isVisible(previewEl)) {
        try {
          const clickTarget = previewEl.closest('.react-player__preview') || previewEl;
          clickTarget.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));

          // Short wait for react-player to mount <youtube-video> or <iframe>
          await new Promise((resolve) => setTimeout(resolve, 350));

          const mountedYt = doc.querySelector('youtube-video');
          if (mountedYt && mountedYt.getAttribute('src')) {
            mediaUrl = mountedYt.getAttribute('src');
          }

          if (!mediaUrl) {
            const mountedIframe = doc.querySelector('iframe[src*="youtube.com"], iframe[src*="youtu.be"]');
            if (mountedIframe && mountedIframe.src) {
              mediaUrl = mountedIframe.src;
            }
          }
        } catch (err) {
          console.warn('[c2b] Could not trigger react-player preview click:', err);
        }
      }
    }

    // 4. Fallback: check standard HTML5 <video>
    if (!mediaUrl) {
      const videoTag = doc.querySelector('video');
      if (videoTag && videoTag.src && !videoTag.src.startsWith('blob:')) {
        mediaUrl = videoTag.src;
      }
    }

    return this._normalizeYouTubeUrl(mediaUrl);
  }

  async _extractCaptions(doc) {
    let captionsText = '';

    // 1. Check if transcription panel is already open in #chat-panel / side-panel
    const transcriptSpans = Array.from(
      doc.querySelectorAll('#chat-panel .css-sjet47 span.chakra-text, #side-panel-content .css-sjet47 span.chakra-text')
    ).filter((el) => this._isVisible(el));

    if (transcriptSpans.length > 0) {
      captionsText = transcriptSpans.map((s) => s.innerText.trim()).filter(Boolean).join(' ');
      if (captionsText.length > 40) return captionsText;
    }

    // 2. If transcription button exists, click it to open the transcript panel
    const btnShowTranscript = doc.querySelector(
      'button[aria-label="Mostrar Transcrição"], button[aria-label="Show Transcript"], button[aria-label="Transcrição"]'
    );

    if (btnShowTranscript && this._isVisible(btnShowTranscript)) {
      try {
        btnShowTranscript.click();
        await new Promise((resolve) => setTimeout(resolve, 400));

        const updatedSpans = Array.from(
          doc.querySelectorAll(
            '#chat-panel .css-sjet47 span.chakra-text, #side-panel-content .css-sjet47 span.chakra-text'
          )
        );

        if (updatedSpans.length > 0) {
          captionsText = updatedSpans.map((s) => s.innerText.trim()).filter(Boolean).join(' ');
          if (captionsText.length > 40) return captionsText;
        }
      } catch (err) {
        console.warn('[c2b] Error triggering transcript button:', err);
      }
    }

    // 3. Fallback: Check tracks or textTracks on video
    const tracks = Array.from(doc.querySelectorAll('track'));
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
          // Ignore
        }
      }
    }

    return captionsText;
  }

  _extractLinks(doc, areaPrincipal, seenUrls) {
    const links = [];
    if (!areaPrincipal) return links;

    // Collect reference links inside markdown content
    areaPrincipal.querySelectorAll('a[href]').forEach((a) => {
      if (!this._isVisible(a)) return;
      if (a.closest('header, nav, aside, [aria-label*="Feedback"]')) return;

      const href = a.href ? a.href.trim() : '';
      const texto = a.innerText.trim() || a.getAttribute('title') || href;

      if (
        href &&
        !href.startsWith('javascript:') &&
        !href.endsWith('#') &&
        !seenUrls.has(href) &&
        href !== window.location.href &&
        href !== window.location.href + '/'
      ) {
        seenUrls.add(href);
        links.push({ texto, url: href });
      }
    });

    return links;
  }

  async extract(doc) {
    const hierarchy = this._extractHierarchy(doc);
    const mediaUrl = await this._extractMediaUrl(doc);
    const captionsText = await this._extractCaptions(doc);

    const areaPrincipal = doc.querySelector('main') || doc.body;
    const seenUrls = new Set();
    const links = this._extractLinks(doc, areaPrincipal, seenUrls);
    const notesText = this._extractNotes(doc, areaPrincipal);

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
  window.UdacityExtractor = UdacityExtractor;
  window.c2bExtractors = window.c2bExtractors || [];
  window.c2bExtractors.push(new UdacityExtractor());
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { UdacityExtractor };
}
