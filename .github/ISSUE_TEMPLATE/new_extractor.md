---
name: New Platform Extractor Request / Proposal
about: Propose adding support for a new course/learning platform
title: "[EXTRACTOR] Support for <Platform Name>"
labels: ["extractor", "enhancement"]
assignees: ""
---

**Platform Name**
Name of the learning platform or LMS (e.g. Skool, Coursera, Udemy, Hotmart, Teachable).

**Platform URL Pattern**
Example URL structure: `https://<subdomain>.platform.com/...`

**Content Types Available on this Platform**
- [ ] Video with HTML5 / WebVTT Captions
- [ ] Rich Text Notes / Transcripts
- [ ] Downloadable Attachments / External Links
- [ ] Embedded Slides or PDF

**DOM Selectors / Structure (if inspected)**
If you have already inspected the DOM of this platform, please list relevant selectors for:
- Course name: `...`
- Lesson title: `...`
- Caption tracks or text: `...`
- Lesson description / notes: `...`

**Are you interested in implementing this extractor?**
- [ ] Yes, I'd like to submit a PR implementing `extension/extractors/<platform>.js`!
- [ ] No, just requesting support from the community.
