---
name: readme-style
description: "Robot URDF Studio 项目专用 README.md 风格规范。基于 text-to-cad、MetaGPT 等主流大型开源项目的排版模式，生成含 Badge 盾牌区、多语言标签切换、ASCII 架构图、特性网格表、文件树架构图、路线图表格的专业 README。Whenever the README.md needs to be created or updated, use this skill."
category: project
risk: safe
source: project
date_added: "2026-05-02"
---

# README Style — Robot URDF Studio

Professional README design standard for this project, modelled after major open-source projects (text-to-cad, MetaGPT, tRPC, etc.).

## Mandatory Sections (in order)

### 1. Badge Shield Bar

Top `<div align="center">` block with `for-the-badge` style shields:

```
Python version | GUI framework | Rendering | Platform | License | Test count | Version
```

Use shields.io `style=for-the-badge`. Each badge gets its own `<img>` tag, horizontally centred.

### 2. Title + One-liner

```
# 🤖 Project Name
**One-line description in bold**
```

### 3. Language Tabs

```html
<p align="center">
  <b><a href="#english">English</a></b> &nbsp;|&nbsp;
  <b><a href="#中文">中文</a></b> &nbsp;|&nbsp;
  <b><a href="#日本語">日本語</a></b>
</p>
```

### 4. Preview / Screenshot

ASCII layout diagram showing the actual UI structure, or a real screenshot/GIF if available.

### 5. English Section

- `## ✨ Features` — 2×2 `<table>` with emoji headers, each cell a bullet list
- `## 🏗 Architecture` — File tree showing package structure with inline comments
- `## 🚀 Quick Start` — Prerequisites, Install, Launch, Run Tests as copy-paste code blocks
- `## ⌨️ Key Bindings` — Compact reference table (if applicable)
- `## 🗺 Roadmap` — Table with Milestone | Focus columns
- `## 🤝 Contributing` — Brief policy aligned with project governance

### 6. Chinese Section (中文)

Same structure as English, all content fully translated.

### 7. Japanese Section (日本語)

Same structure as English, all content fully translated.

### 8. License Footer

```
## 📄 License
MIT License — see the LICENSE file for details.
```

### 9. Tech Stack Footer

```html
<p align="center">
  <sub>Built with Python · PySide6 · OpenGL · CadQuery · trimesh</sub>
</p>
```

## Design Rules

1. **Badges first** — They establish credibility immediately.
2. **Language tabs before content** — Users pick their language before scrolling.
3. **Each language is ONE `<h2>` block** — Never interleave languages.
4. **Features use `<table>` not paragraphs** — Scannable, compact, professional.
5. **Code blocks are copy-paste ready** — No placeholders; real commands that work.
6. **Architecture uses tree + inline comments** — Shows structure AND purpose simultaneously.
7. **Roadmap uses a table** — Milestones left, focus right. No prose.
8. **No wall-of-text** — Every section should be digestible in 10 seconds.
9. **Emoji headers** — Visual anchors for section scanning (✨ 🏗 🚀 ⌨️ 🗺 🤝 📄).
10. **Shields use `for-the-badge`** — Larger, more prominent than default style.

## Checklist Before Commit

- [ ] All badge URLs load correctly
- [ ] Language anchor links (`#english`, `#中文`, `#日本語`) all work
- [ ] ASCII diagram renders correctly in monospace (no broken borders)
- [ ] All `git clone` / `pip install` / launch commands are tested
- [ ] File tree accurately reflects current project structure
- [ ] Roadmap table matches VERSIONING.md
- [ ] No hardcoded version numbers outside the badge bar
- [ ] Three languages are complete (no untranslated sections)
