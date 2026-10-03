/**
 * course2brain - Skilljar Platform Extractor
 * Handles courses, topics, modular lessons, and embedded YouTube videos on Skilljar (e.g. Anthropic Partners).
 */

class SkilljarExtractor extends (typeof BaseExtractor !== 'undefined' ? BaseExtractor : class {}) {
  get platformId() {
    return 'skilljar';
  }

  get platformName() {
    return 'Skilljar';
  }

  canHandle(url, doc) {
    if (!url) return false;
    const isSkilljarDomain =
      url.includes('skilljar.com') ||
      url.includes('anthropic-partners.skilljar.com');

    const hasSkilljarElements = !!doc.querySelector(
      '#lp-left-nav, .lessons-wrapper, #curriculum-list-2, #curriculum-list, sjwc-lesson-content-item, .lesson-modular'
    );

    return isSkilljarDomain || hasSkilljarElements;
  }

  _isVisible(el) {
    if (!el) return false;
    if (el.closest('.hidden') || el.closest('[hidden]')) return false;
    return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  }

  _extractYouTubeId(url) {
    if (!url) return null;
    const match = url.match(/(?:v=|\/embed\/|youtu\.be\/|\/v\/)([a-zA-Z0-9_-]{11})/);
    return match ? match[1] : null;
  }

  _extractHierarchy(doc) {
    let courseName = '';
    let sectionName = null;
    let formattedTitle = '';

    // 1. Program / Course Title (e.g. "AI Fluency: Framework & Foundations")
    const titleEl = doc.querySelector(
      '#lp-left-nav h1.course-title, .lp-left-nav .course-title, h1.course-title, [class*="course-title"]'
    );
    if (titleEl) {
      const clone = titleEl.cloneNode(true);
      clone.querySelectorAll('.sj-course-time, span, svg, button').forEach((el) => el.remove());
      const text = clone.innerText.trim();
      if (text && text.length > 2) courseName = text;
    }

    if (!courseName) {
      const ogTitle = doc.querySelector('meta[property="og:title"]')?.getAttribute('content')?.trim();
      if (ogTitle && ogTitle.includes('|')) {
        courseName = ogTitle.split('|')[0].trim();
      } else {
        const rawTitle = doc.title || '';
        courseName = rawTitle.includes('|') ? rawTitle.split('|')[0].trim() : 'Curso Skilljar';
      }
    }

    // 2. Topics (Sections) and Modular Lessons from Navigation Menu
    const curriculumWrapper = doc.querySelector('#curriculum-list-2, .lessons-wrapper, #curriculum-list');
    if (curriculumWrapper) {
      const allElements = Array.from(
        curriculumWrapper.querySelectorAll('h3.section-title, a.lesson, .lesson-row')
      );

      // Normalize into ordered nodes: sections and lesson links
      const curriculumNodes = [];
      const seenLessons = new Set();

      for (const el of allElements) {
        if (el.matches('h3.section-title') || el.classList.contains('section-title')) {
          curriculumNodes.push({ type: 'section', el });
        } else {
          const lessonLink = el.matches('a.lesson') ? el : el.closest('a.lesson');
          if (lessonLink && !seenLessons.has(lessonLink)) {
            seenLessons.add(lessonLink);
            curriculumNodes.push({ type: 'lesson', el: lessonLink });
          }
        }
      }

      let currentSectionIdx = 0;
      let currentSectionTitle = '';
      let currentLessonIdx = 0;
      let matchedSection = null;
      let matchedLesson = null;
      let matchedLessonIdx = -1;

      const currentPath = typeof window !== 'undefined' && window.location ? window.location.pathname : '';

      for (const node of curriculumNodes) {
        if (node.type === 'section') {
          currentSectionIdx++;
          currentLessonIdx = 0;
          currentSectionTitle = node.el.innerText.trim();
        } else if (node.type === 'lesson') {
          currentLessonIdx++;
          const lessonEl = node.el;

          const isAriaCurrent = lessonEl.getAttribute('aria-current') === 'page';
          const hasActiveRow = !!lessonEl.querySelector('.lesson-active, .theme-color-bg');
          const href = lessonEl.getAttribute('href') || '';
          const matchesPath = href && currentPath && (currentPath.endsWith(href) || currentPath.includes(href));

          if (isAriaCurrent || hasActiveRow || matchesPath) {
            const paddedSectionNum = String(currentSectionIdx || 1).padStart(2, '0');
            const safeSectionTitle = currentSectionTitle || 'Módulo Principal';
            matchedSection = /^\d+[\s.-]/.test(safeSectionTitle)
              ? safeSectionTitle
              : `${paddedSectionNum} - ${safeSectionTitle}`;

            matchedLesson = lessonEl;
            matchedLessonIdx = currentLessonIdx;
            break;
          }
        }
      }

      if (matchedLesson) {
        sectionName = matchedSection;

        const rowEl = matchedLesson.querySelector('.lesson-row');
        let rawLessonTitle = (rowEl?.getAttribute('title') || '').trim();

        if (!rawLessonTitle) {
          const titleDiv = matchedLesson.querySelector('.title');
          if (titleDiv) {
            const clone = titleDiv.cloneNode(true);
            clone.querySelectorAll('.sj-lesson-time, span').forEach((s) => s.remove());
            rawLessonTitle = clone.innerText.trim();
          } else {
            rawLessonTitle = matchedLesson.innerText.trim();
          }
        }

        // Clean any residual duration string at end (e.g. " 5 min")
        rawLessonTitle = rawLessonTitle.replace(/\s+\d+\s*(?:min|mins|sec|hr|hrs)?$/i, '').trim();

        const paddedLessonNum = String(matchedLessonIdx).padStart(2, '0');
        formattedTitle = /^\d+[\s.-]/.test(rawLessonTitle)
          ? rawLessonTitle
          : `${paddedLessonNum}. ${rawLessonTitle}`;
      }
    }

    // 3. Fallbacks if active item was not matched in sidebar
    if (!formattedTitle) {
      const heading = doc.querySelector(
        '#lesson-main-content h2.post-heading, #lesson-main-content h2, #lesson-main-content h1'
      );
      if (heading) {
        formattedTitle = heading.innerText.trim();
      } else {
        formattedTitle = doc.title ? doc.title.split('|')[0].trim() : 'Aula Skilljar';
      }
    }

    return {
      course_name: courseName,
      space_name: null,
      section_name: sectionName,
      title: formattedTitle,
    };
  }

  _htmlToMarkdown(element) {
    if (!element) return '';
    const clone = element.cloneNode(true);

    // Remove UI widgets, svg icons, scripts, styles, iframes, feedback buttons
    clone
      .querySelectorAll('script, style, button, svg, sjwc-icon, iframe, .animated-button-pair, [role="progressbar"]')
      .forEach((el) => el.remove());

    // Convert headings
    clone.querySelectorAll('h1').forEach((h) => h.replaceWith(`\n# ${h.innerText.trim()}\n`));
    clone.querySelectorAll('h2').forEach((h) => h.replaceWith(`\n## ${h.innerText.trim()}\n`));
    clone.querySelectorAll('h3').forEach((h) => h.replaceWith(`\n### ${h.innerText.trim()}\n`));
    clone.querySelectorAll('h4').forEach((h) => h.replaceWith(`\n#### ${h.innerText.trim()}\n`));
    clone.querySelectorAll('h5').forEach((h) => h.replaceWith(`\n##### ${h.innerText.trim()}\n`));

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

    // Primary: Skilljar custom web component container
    const contentItem = doc.querySelector('#lesson-main-content sjwc-lesson-content-item, sjwc-lesson-content-item');
    if (contentItem) {
      notes = this._htmlToMarkdown(contentItem);
    }

    if (!notes && mainEl) {
      const lessonContainer = doc.querySelector('#lesson-main-content') || mainEl;
      notes = this._htmlToMarkdown(lessonContainer);
    }

    return notes;
  }

  _extractMediaUrl(doc) {
    // 1. Check for embedded YouTube iframe
    const iframe = doc.querySelector(
      'iframe[src*="youtube.com/embed/"], iframe[src*="youtube-nocookie.com/embed/"], iframe[src*="youtube.com"], iframe[src*="youtu.be"]'
    );
    if (iframe && iframe.src) {
      const ytId = this._extractYouTubeId(iframe.src);
      if (ytId) {
        return `https://www.youtube.com/watch?v=${ytId}`;
      }
      return iframe.src;
    }

    // 2. Check for HTML5 <video>
    const video = doc.querySelector('video');
    if (video && video.src && !video.src.startsWith('blob:')) {
      return video.src;
    }

    return null;
  }

  _extractLinks(doc, areaPrincipal, seenUrls) {
    const links = [];
    if (!areaPrincipal) return links;

    areaPrincipal.querySelectorAll('a[href]').forEach((a) => {
      if (!this._isVisible(a)) return;
      if (a.closest('#lp-left-nav, nav, header, aside, .left-nav-return')) return;

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
    const mediaUrl = this._extractMediaUrl(doc);
    const areaPrincipal = doc.querySelector('#lesson-main-content') || doc.querySelector('main') || doc.body;

    const seenUrls = new Set();
    const links = this._extractLinks(doc, areaPrincipal, seenUrls);
    const notesText = this._extractNotes(doc, areaPrincipal);

    return {
      platform: this.platformId,
      course_name: hierarchy.course_name,
      space_name: hierarchy.space_name,
      section_name: hierarchy.section_name,
      title: hierarchy.title,
      captions_text: '', // Captions for YouTube videos are automatically resolved on the backend
      notes_text: notesText,
      links: links,
      page_url: window.location.href,
      media_url: mediaUrl,
    };
  }
}

// Self-register in browser context
if (typeof window !== 'undefined') {
  window.SkilljarExtractor = SkilljarExtractor;
  window.c2bExtractors = window.c2bExtractors || [];
  window.c2bExtractors.push(new SkilljarExtractor());
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { SkilljarExtractor };
}
