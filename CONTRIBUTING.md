# Contributing to course2brain

Thank you for your interest in contributing to **course2brain**! We welcome community contributions, from reporting bugs and suggesting new features to implementing new platform extractors and improving documentation.

---

## 🛠️ Development Setup

This project uses [`uv`](https://docs.astral.sh/uv/) for high-speed Python dependency management.

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/<your-username>/course2brain.git
   cd course2brain
   ```

2. **Install dependencies and create virtual environment:**
   ```bash
   uv sync
   ```

3. **Run the test suite:**
   ```bash
   uv run pytest
   ```

4. **Run code linting and formatting checks:**
   ```bash
   uv run ruff check .
   uv run ruff format --check .
   ```

---

## 🧩 Adding a New Platform Extractor

The Chrome extension uses an extensible **Strategy Pattern** for extracting course data. To support a new course or community platform (e.g. Skool, Teachable, Hotmart):

1. Create a new extractor in `extension/extractors/<platform>.js`.
2. Extend `BaseExtractor` from `base.js`:
   ```javascript
   import { BaseExtractor } from './base.js';

   export class MyPlatformExtractor extends BaseExtractor {
     canHandle(url, doc) {
       return url.includes('myplatform.com');
     }

     async extract(doc) {
       return {
         platform: 'myplatform',
         course_name: this._detectCourseName(doc),
         title: this._detectTitle(doc),
         captions_text: await this._extractCaptions(doc),
         notes_text: this._extractNotes(doc),
         links: this._extractLinks(doc),
         page_url: window.location.href,
       };
     }
   }
   ```
3. Register your extractor in `extension/content.js`.
4. Test with active lessons on the platform.

---

## 📝 Commit Guidelines (Conventional Commits)

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` A new feature or extractor (e.g., `feat(extractors): add skool platform support`)
- `fix:` A bug fix (e.g., `fix(circle): handle hidden syllabus fallback elements`)
- `docs:` Documentation changes (e.g., `docs: add quickstart guide`)
- `refactor:` Code improvements without behavioral changes
- `test:` Adding or updating tests
- `chore:` Maintenance tasks, dependency updates, CI workflows

---

## 🚀 Submitting a Pull Request

1. Create a feature branch:
   ```bash
   git checkout -b feat/my-new-feature
   ```
2. Make your changes and ensure all tests pass (`uv run pytest && uv run ruff check .`).
3. Commit with a descriptive message following Conventional Commits.
4. Push your branch and open a Pull Request against `main`.
5. Fill out the PR template thoroughly.

---

## 📜 Code of Conduct

Please review and adhere to our [Code of Conduct](CODE_OF_CONDUCT.md) in all project interactions.
