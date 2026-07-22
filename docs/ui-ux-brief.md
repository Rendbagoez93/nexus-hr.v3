# UI/UX Brief — Nexus HR

**Version**: 1.2 | **Date**: July 2026 | **Status**: Active Development

> Derived from `design.md` and `frontend-styling-guide.md`.

---

## 1. Design Direction

Nexus HR is a **dark-themed, professional SaaS dashboard** for HR operations in Indonesian industrial companies.

### Design Principles

1. **Data first, chrome second** — every pixel communicates data, hierarchy, or interaction affordance
2. **One primary action per view** — exactly one `btn-primary` per visible area
3. **Status is always visible** — communicated with both colour AND label (never colour alone)
4. **Predictable structure** — fixed nav → page hero/header → content grid → footer
5. **Conservative motion** — animation confirms actions or reveals content; never for delight alone

### Design Language

- Industrial credibility — dense but structured
- Hierarchy at a glance — primary, secondary, status info within 2 seconds
- Dark-first — no light mode
- Full design system is dark-only

---

## 2. Color Palette

### Background Layers (darkest → lightest)

| Layer | Token | Hex | Use |
|-------|-------|-----|-----|
| Page base | `--color-bg` | `#0a0f1e` | `<body>`, default section background |
| Alternate band | `--color-bg-card-2` | `#161d2e` | Every other section, sidebar, data tables |
| Card surface | `--color-bg-card` | `#111827` | Cards, modals, dropdowns, inputs |

Alternate sections by zebra-striping between `--color-bg` and `--color-bg-card-2`.

### Brand Palette

| Token | Hex | Use |
|-------|-----|-----|
| `--color-primary` | `#3b82f6` | Buttons, active states, links, focus rings |
| `--color-primary-dk` | `#2563eb` | Button hover/pressed |
| `--color-primary-lt` | `#60a5fa` | Text on dark backgrounds, links |
| `--color-accent` | `#06b6d4` | Gradient pair with primary, chart highlights |

**Brand gradient**: `linear-gradient(135deg, --color-primary-lt, --color-accent)` — never invert or add a third color.

### Semantic Colors

| Token | Hex | Use |
|-------|-----|-----|
| `--color-success` | `#10b981` | Clocked in, approved, compliant, active |
| `--color-warning` | `#f59e0b` | Pending, expiring soon, requires attention |
| `--color-danger` | `#ef4444` | Error, rejected, overdue, critical violation |

### Text Hierarchy

| Token | Hex | Use |
|-------|-----|-----|
| `--color-text` | `#f1f5f9` | Primary — headings, values, important data |
| `--color-text-muted` | `#94a3b8` | Body copy, descriptions, secondary info |
| `--color-text-subtle` | `#64748b` | Labels, captions, timestamps, helper text |

**Rule**: Interactive text must use `--color-text` or `--color-primary-lt`, never `--color-text-subtle`.

### Borders

Single border token: `--color-border` (`#1f2d47`). Active borders: `rgba(59,130,246,0.4)`.

### Status Colors

| Status | Background | Text |
|--------|-----------|------|
| Active / Clocked In / Approved | `rgba(16,185,129,0.15)` | `#34d399` |
| Informational / On Leave | `rgba(59,130,246,0.15)` | `#60a5fa` |
| Pending / Warning | `rgba(245,158,11,0.15)` | `#fbbf24` |
| Error / Rejected / Danger | `rgba(239,68,68,0.15)` | `#f87171` |

Formula: `background: rgba(COLOR_RGB, 0.15)`, `color: LIGHTER_TONE`, `border-radius: 999px`.

### Icon Tint Containers

Six tints at 12% opacity for `52×52px` icon containers: `icon-blue`, `icon-cyan`, `icon-green`, `icon-amber`, `icon-purple`, `icon-rose`.

---

## 3. Typography

**Typeface**: Inter (Google Fonts) — weights 300, 400, 500, 600, 700, 800. No other typeface.

### Type Scale

| Role | Size | Weight | Letter-spacing | Line-height |
|------|------|--------|----------------|-------------|
| Hero headline | `clamp(38px, 5vw, 60px)` | 800 | `-2px` | 1.1 |
| Section title | `clamp(30px, 4vw, 44px)` | 800 | `-1.5px` | 1.15 |
| CTA title | `clamp(30px, 4vw, 48px)` | 800 | `-1.5px` | 1.15 |
| Card heading | `20px` | 700 | `-0.3px` | default |
| Step / sub-heading | `18px` | 700 | none | default |
| Large body | `18px` | 400 | none | 1.7 |
| Body | `15px` | 400 | none | 1.65 |
| Small body | `14px` | 400–500 | none | 1.4–1.65 |
| Label / meta | `13px` | 500–600 | none | default |
| Tag pill | `10px–12px` | 600 | `0.05em` | default |
| ALL-CAPS label | `11px–13px` | 600–700 | `0.04–0.05em` | default |

### Typography Rules

- Negative letter-spacing on large headings is mandatory (optical expansion on dark)
- ALL-CAPS must use `letter-spacing: 0.04em` minimum
- Use `clamp()` for headings across viewports
- Body text max-width: `560px` at center-aligned layouts
- Global base `line-height: 1.6`
- Bold inline: `font-weight: 600`, not 700

---

## 4. Spacing System

| Step | Value | Use |
|------|-------|-----|
| 2xs | 4px | Tag internal padding (vertical) |
| xs | 6–8px | Gap between inline elements, icon margins |
| sm | 10–12px | Button padding (vertical) |
| md | 14–16px | Card internal padding (tight) |
| base | 20–24px | Card padding (standard), container horizontal padding |
| lg | 28–32px | Card padding (generous), step card padding |
| xl | 36–40px | Feature card padding, hero action gap |
| 2xl | 48px | Section strips, footer top padding, compliance grid gap |
| 3xl | 64px | Section margin-bottom for headers |
| 4xl | 96px | Standard section vertical padding |

---

## 5. Elevation & Depth

### Hierarchy

```text
Page background (no border, no shadow)
└── Section band (background change only)
    └── Card (border + optional shadow)
        └── Modal (border + shadow-card + shadow-glow)
    └── Floating card (shadow-card + animation)
```

### Shadows

| Token | Value | Use |
|-------|-------|-----|
| `--shadow-card` | `0 4px 24px rgba(0,0,0,0.4)` | Modals, dropdowns, floating elements |
| `--shadow-glow` | `0 0 40px rgba(59,130,246,0.18)` | Hero elements, paired with shadow-card |

Hover: `box-shadow: 0 8px 32px rgba(59,130,246,0.12)` (blue-tinted).

### Border Radius

| Token | Value |
|-------|-------|
| `--radius-sm` | 6px |
| `--radius-md` | 12px |
| `--radius-lg` | 20px |

---

## 6. Layout System

### Container

- Max-width: `1200px`, centered, `24px` horizontal padding
- Never apply width constraints to `<section>` directly — use `.container` wrapper

### Page Structure

```text
Fixed Nav (64px height, z-index 100)
├─ Hero Section (min-height 100vh, padding-top 120px)
├─ Logo / Industry Strip (padding 48px 0)
├─ Content Section A (padding 96px 0, bg: --color-bg)
├─ Stats Band (padding 64px 0, bg: --color-bg-card-2)
├─ Content Section B (padding 96px 0, bg: --color-bg)
├─ CTA Band (bg: --color-bg-card-2, border-top + border-bottom)
└─ Footer (padding 64px 0 32px)
```

### Grid Patterns

| Context | Columns | Gap |
|---------|---------|-----|
| Hero (copy + visual) | `1fr 1fr` | 64px |
| Feature cards | `repeat(2, 1fr)` | 24px |
| Industry cards | `repeat(4, 1fr)` | 20px |
| Stats | `repeat(4, 1fr)` | 24px |
| Process steps | `repeat(3, 1fr)` | 32px |
| Compliance | `1fr 1fr` | 48px |
| Footer | `2fr 1fr 1fr 1fr` | 48px |

**CSS Grid is mandatory for multi-column content grids.** Flexbox for single-axis alignment only.

### Section Header Anatomy

```text
[TAG PILL]      ← ALL-CAPS module label
[Section Title] ← h2, sentence case
[Description]   ← 1–2 sentences, max 560px wide
```

`margin-bottom: 64px` before content grid begins.

---

## 7. Component Design

### Tag Pill

- Blue (12% tint) background for informational use
- Above section title, ALL-CAPS, 1–3 words
- Optional pulsing dot for live/active items

### Buttons

| Variant | Use |
|---------|-----|
| `btn-primary` | Main CTA (one per area) |
| `btn-ghost` | Secondary nav actions |
| `btn-outline` | Secondary CTA alongside primary |

Sizes: `btn-xl` (hero CTAs), `btn-lg` (modal actions), default (nav/inline).

Hover rules:
- `btn-primary`: `translateY(-1px)` + blue box-shadow
- `btn-outline`: border turns primary + ring effect
- `btn-ghost`: text color shifts to `--color-text`

### Cards

```text
┌──────────────────────────────────┐ ← 1px border
│ [Icon container] 52×52           │
│ Card Title 20px/700              │
│ Description text 15px/muted      │
│ • List item (::before ✓)         │
└──────────────────────────────────┘
↑ 2px gradient top bar (hidden → visible on hover)
```

Hover: gradient visible + border turns blue + `translateY(-4px)` + blue shadow. All four fire together.

### Data List Rows

- Initials avatar: brand gradient background, `#fff` text, `700` weight
- Name, status label layout

### Stat Cards

- Number: gradient text (primary-lt → accent)
- Animated counter (ease-out cubic, 1400ms)
- Label: `--color-text-muted`

### Step / Process Cards

- Numbered circular indicator with primary tint
- `→` connector between cards (hidden on mobile)

### Floating Cards

- Decorative only, max 2 per visual element
- Different `animation-delay` each
- Remove at ≤ 1024px

### Form Inputs

- Background: `--color-bg-card`
- Border: `--color-border`
- Focus: `border-color: --color-primary` + `box-shadow: 0 0 0 2px rgba(59,130,246,0.2)`
- Error: `border-color: --color-danger` + error message below field
- Labels: 13px, weight 500, `--color-text-muted`

---

## 8. Navigation

### Structure

```text
[Logo mark + name]    [Nav links]    [CTA buttons]
left                  center         right
```

- Fixed bar: `position: fixed; top: 0; z-index: 100`
- Logo mark: `36×36px` rounded gradient square + initial letter
- Logo name: `20px`, weight 700

### Scroll State

- Before scroll: transparent background, transparent border
- After 40px scroll: `background: rgba(10,15,30,0.85)` + `backdrop-filter: blur(16px)` + border

### Nav Links

- `--color-text-muted` at rest, `--color-text` on hover
- 14px, weight 500, 32px gap

### Nav CTAs

- Exactly 2: `btn-ghost` + `btn-primary`

### Mobile (≤ 768px)

- Nav links hidden
- CTA buttons remain

---

## 9. Motion & Animation

### Motion Budget (max 3 types per page)

1. Scroll reveal (`.reveal` + IntersectionObserver) — universal
2. One ambient loop (float or pulse) — hero only
3. One data animation (counter) — stats only

### Scroll Reveal

- `.reveal`: `opacity: 0; translateY(24px)` → `.visible`: `opacity: 1; translateY(0)`
- Duration: 0.6s ease
- Stagger: `.reveal-delay-1` through `.reveal-delay-4` (0.1s–0.4s)
- Applied to: section headers, cards, compliance indicators, stat cards
- NOT applied to: nav, hero headline, footer

### Float Animation

- `translateY(0) → translateY(-10px)`, 6–7s ease-in-out infinite
- Only on: dashboard mock card, floating accent cards
- Never on content cards or interactive elements

### Duration Standards

| Interaction | Duration |
|-------------|----------|
| Color/border transitions | 0.2s |
| Card hover lift + shadow | 0.3s |
| Scroll reveal fade-in | 0.6s |
| Counter animation | 1400ms |
| Float loop | 6–7s |
| Glassmorphism nav | 0.3s |

### Easing

| Use | Easing |
|-----|--------|
| Hover transitions | ease |
| Scroll reveal | ease |
| Counter | ease-out cubic |
| Float | ease-in-out |

Never `linear` for UI. Never `ease-in` for reveals.

---

## 10. Responsive Behaviour

### Breakpoints

| Name | Max-width | Key Changes |
|------|-----------|-------------|
| Tablet | 1024px | Hero → 1-column, visual hidden, stats/industries → 2-col, footer → 2-col |
| Mobile | 768px | Nav links hidden, all grids → 1-col, section padding → 64px, step connectors hidden |
| Small mobile | 480px | Stats/industries → 2-col, hero buttons stack vertically at 100% width |

### Responsive Rules

- Hero visual panel: hidden at ≤ 1024px
- Nav links: hidden at ≤ 768px
- Buttons: full-width at ≤ 480px, flex stacks vertically
- Step connectors: hidden on mobile
- Grid minimum column: 280px before collapsing

---

## 11. Accessibility

- All body text meets WCAG AA (≥ 4.5:1 contrast ratio)
- Status never relies on color alone — always paired with text label
- Focus ring: `box-shadow: 0 0 0 2px var(--color-primary)` — never `outline: none` without replacement
- `prefers-reduced-motion` respected — disables all animations
- Semantic HTML: `<nav>`, `<section>`, `<h1>` once per page, `<footer>`, `<a>` for nav, `<button>` for actions
- Alt text on all meaningful images
- `aria-label` on icon-only buttons

---

## 12. Writing Style

| Element | Convention |
|---------|-----------|
| Tone | Professional but direct — for busy, experienced HR admins |
| Section titles | Sentence case: "Everything HR, in one platform" |
| Proper nouns | Retain casing: "PPh 21", "BPJS Kesehatan", "ISO 45001" |
| Tag pills / column headers | ALL-CAPS: "CORE MODULES" |
| Status labels | Title Case: "Clocked In", "On Leave" |
| Nav links | Title Case: "Features", "How It Works" |
| CTAs | Active verb + noun: "Explore Features", "Get Started" |
| Numbers | Comma separator: "1,200 employees" |

---

## 13. Django Template Integration

### Template Inheritance

```text
base.html ← head, nav, footer, script tags
├── index.html ← hero + landing sections
├── dashboard.html
├── employees/
│   ├── list.html
│   └── detail.html
```

### Rules

- Always `{% load static %}` as first line
- Always `{% static 'path' %}` for asset URLs
- `<script>` tags at end of `<body>`
- Per-page CSS via `{% block extra_css %}`, JS via `{% block extra_js %}`
- Never use Django's default form rendering without overriding widget templates

---

## 14. CSS / JS File Conventions

### CSS File Order

1. Reset & Base
2. CSS custom properties (`:root` block)
3. Utility classes
4. Navigation
5. Page-specific components (in DOM order)
6. Scroll reveal / animation helpers
7. Responsive media queries (always last)

### Naming

| Type | Convention | Example |
|------|-----------|---------|
| CSS classes | kebab-case | `.feature-card`, `.nav-logo-mark` |
| Section IDs | kebab-case | `id="how-it-works"` |
| JS variables | camelCase | `revealEls`, `counterObserver` |
| Data attributes | `data-kebab-case` | `data-target="500"` |
| Template files | snake_case | `leave_request_list.html` |

### JavaScript Patterns

- Vanilla JS only — no jQuery, no framework
- Nav scroll state via `window.scrollY > 40` toggle
- Scroll reveal via `IntersectionObserver` (threshold 0.12, rootMargin -40px bottom)
- Animated counters via `requestAnimationFrame` + `performance.now()` + ease-out cubic
- Smooth scroll for anchor links with 80px nav offset
- All scroll listeners use `{ passive: true }`
