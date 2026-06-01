# Design Identity

A specification document defining the deliberate aesthetic, tonal, and structural choices that distinguish this product from training-data defaults. Complete this document during Phase 1 (Architecture) before any user-facing casting begins. Design tokens derived from this document become SDK building blocks.

## Product Identity

**Product name:** _[Name]_

**What is this product?** _[One-sentence description of what it does]_

**Who uses it?** _[Primary user personas and their context]_

**What feeling should it evoke?** _[The emotional response a user should have: confidence, delight, calm, urgency, etc. Be specific, not generic.]_

## Aesthetic Direction

Choose a specific, named aesthetic direction. Do not use "modern," "clean," or "professional" without qualification. These terms map to training-data defaults and produce generic output.

**Direction:** _[e.g., "Industrial minimalism with warm accents," "Dense editorial with sharp typography," "Brutalist with deliberate softness at interaction points," "Retro-futuristic data visualization"]_

**Rationale:** _[Why this direction fits the product, the users, and the market position]_

**Inspiration/reference targets:** _[3-5 specific products, sites, or design systems whose aesthetic anchors this direction. Include URLs where possible.]_

1. _[Reference 1 and what to take from it]_
2. _[Reference 2 and what to take from it]_
3. _[Reference 3 and what to take from it]_

## Anti-Patterns and Slop Fingerprints

Patterns that this project must not exhibit. These are checked by divergence gates during quality gate execution.

### Banned Visual Patterns

- _[e.g., "Inter, Roboto, or Arial as body font"]_
- _[e.g., "Purple-to-blue gradient hero sections"]_
- _[e.g., "Three-column feature grids with identical card sizing"]_
- _[e.g., "Glassmorphism cards with blur backgrounds"]_
- _[e.g., "Lucide/Heroicons in tinted circles as feature icons"]_

### Banned Copy Patterns

- _[e.g., "'Unlock the power of...' headlines"]_
- _[e.g., "'Your all-in-one solution for...' taglines"]_
- _[e.g., "'Something went wrong. Please try again later.' error messages"]_
- _[e.g., "Generic CTAs: 'Get Started', 'Learn More' without product-specific language"]_

### Banned Structural Patterns

- _[e.g., "Hero, Features Grid, Social Proof, Pricing, FAQ, Footer page structure"]_
- _[e.g., "'Most Popular' pricing pill with gradient border"]_
- _[e.g., "Five-star testimonial rows with DiceBear avatar fallbacks"]_

## Typography System

All type values become design tokens in the SDK. Agents reference tokens, not raw font declarations.

**Display font:** _[Font name]_
**Display rationale:** _[Why this font, what character it brings, how it differs from defaults]_

**Body font:** _[Font name]_
**Body rationale:** _[Why this font, readability considerations, pairing logic]_

**Monospace font (if applicable):** _[Font name]_

### Type Scale

| Token | Size | Weight | Line Height | Letter Spacing | Usage |
|-------|------|--------|-------------|----------------|-------|
| `type.xs` | _[value]_ | _[value]_ | _[value]_ | _[value]_ | _[Labels, captions]_ |
| `type.sm` | _[value]_ | _[value]_ | _[value]_ | _[value]_ | _[Secondary text]_ |
| `type.base` | _[value]_ | _[value]_ | _[value]_ | _[value]_ | _[Body text]_ |
| `type.lg` | _[value]_ | _[value]_ | _[value]_ | _[value]_ | _[Lead text]_ |
| `type.xl` | _[value]_ | _[value]_ | _[value]_ | _[value]_ | _[Section headings]_ |
| `type.2xl` | _[value]_ | _[value]_ | _[value]_ | _[value]_ | _[Page headings]_ |
| `type.3xl` | _[value]_ | _[value]_ | _[value]_ | _[value]_ | _[Hero headings]_ |

## Color System

All color values become design tokens. OKLCH color space is recommended for perceptual uniformity. Include WCAG contrast validation for every text/background pairing.

**Harmony rule:** _[Complementary, analogous, triadic, split-complementary, or custom]_

**Color distribution model:** _[e.g., 60-30-10, monochrome 90/10, high-contrast 50/50, analogous wash]_

### Primary Palette

| Token | Value | Role |
|-------|-------|------|
| `color.primary.50` | _[value]_ | _[Lightest tint, backgrounds]_ |
| `color.primary.100` | _[value]_ | _[...]_ |
| `color.primary.200` | _[value]_ | _[...]_ |
| `color.primary.300` | _[value]_ | _[...]_ |
| `color.primary.400` | _[value]_ | _[...]_ |
| `color.primary.500` | _[value]_ | _[Base, primary actions]_ |
| `color.primary.600` | _[value]_ | _[...]_ |
| `color.primary.700` | _[value]_ | _[...]_ |
| `color.primary.800` | _[value]_ | _[...]_ |
| `color.primary.900` | _[value]_ | _[Darkest shade, text on light]_ |

_Repeat for secondary, accent, neutral, success, warning, error, and info palettes as needed._

### WCAG Contrast Validation

| Text Token | Background Token | Contrast Ratio | Passes AA | Passes AAA |
|------------|-----------------|----------------|-----------|------------|
| _[token]_ | _[token]_ | _[ratio]_ | _[Yes/No]_ | _[Yes/No]_ |

## Spatial System

All spacing values become design tokens.

**Base unit:** _[e.g., 4px]_

**Density philosophy:** _[e.g., "Generous negative space with deliberate density in data regions" or "Compact editorial with breathing room at section boundaries"]_

### Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| `space.2xs` | _[value]_ | _[Inline padding, icon gaps]_ |
| `space.xs` | _[value]_ | _[...]_ |
| `space.sm` | _[value]_ | _[...]_ |
| `space.md` | _[value]_ | _[...]_ |
| `space.lg` | _[value]_ | _[...]_ |
| `space.xl` | _[value]_ | _[...]_ |
| `space.2xl` | _[value]_ | _[...]_ |
| `space.3xl` | _[value]_ | _[Section separation]_ |

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `radius.sm` | _[value]_ | _[...]_ |
| `radius.md` | _[value]_ | _[...]_ |
| `radius.lg` | _[value]_ | _[...]_ |
| `radius.full` | _[value]_ | _[Circular elements]_ |

### Elevation / Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `shadow.sm` | _[CSS box-shadow]_ | _[...]_ |
| `shadow.md` | _[CSS box-shadow]_ | _[...]_ |
| `shadow.lg` | _[CSS box-shadow]_ | _[...]_ |

### Breakpoints

| Token | Value | Description |
|-------|-------|-------------|
| `breakpoint.sm` | _[value]_ | _[Mobile]_ |
| `breakpoint.md` | _[value]_ | _[Tablet]_ |
| `breakpoint.lg` | _[value]_ | _[Desktop]_ |
| `breakpoint.xl` | _[value]_ | _[Large desktop]_ |

## Motion Philosophy

**Principle:** _[e.g., "Purposeful transitions only. Nothing animates for decoration. Entry reveals are staggered. Hover states are instant." or "Fluid and organic. Every state change has a transition. Scroll-triggered reveals create narrative flow."]_

**Timing:** _[Default duration, easing curve]_

**What animates:** _[Page transitions, element entry, hover states, loading states, data changes]_

**What does not animate:** _[Static content, navigation, form inputs, or whatever the identity requires]_

## Accessibility Commitments

Accessibility is a specification constraint, not a testing afterthought. These commitments feed into test molds and quality gates.

**Target WCAG level:** _[A / AA / AAA. AA recommended as minimum for production products.]_

**Contrast requirements:**
- Body text on background: _[minimum ratio, e.g., 4.5:1 for AA normal text]_
- Large text on background: _[minimum ratio, e.g., 3:1 for AA large text]_
- Interactive element boundaries: _[minimum ratio, e.g., 3:1 for UI components]_
- Validate all text/background pairings from the Color System section against these ratios.

**Keyboard navigation:**
- [ ] All interactive elements reachable via Tab/Shift+Tab
- [ ] All interactive elements operable via Enter/Space
- [ ] Visible focus indicators on all focusable elements
- [ ] Logical tab order matching visual layout
- [ ] No focus traps (Escape exits modals and dropdowns)

**Screen reader support:**
- [ ] Semantic HTML used (headings, landmarks, lists, buttons)
- [ ] ARIA attributes only when native semantics are insufficient
- [ ] Meaningful alt text for informative images; decorative images marked `alt=""`
- [ ] Form inputs have associated labels
- [ ] Dynamic content changes announced to screen readers

**Motion and animation:**
- [ ] Respect `prefers-reduced-motion` media query
- [ ] No auto-playing animations that cannot be paused
- [ ] Essential animations have reduced-motion alternatives

**Touch targets:**
- Minimum interactive target size: _[e.g., 44x44 CSS pixels per WCAG 2.5.5]_

**Additional commitments:**
- _[Project-specific accessibility goals]_

## Copy Voice

**Tone:** _[e.g., "Direct and confident, never salesy. Technical precision with warmth. First person plural."]_

**Vocabulary constraints:** _[Domain-specific terms to use, generic terms to avoid]_

### Banned Phrases

- _[e.g., "Unlock the power of..."]_
- _[e.g., "Seamlessly integrate..."]_
- _[e.g., "Your all-in-one solution..."]_
- _[e.g., "Something went wrong. Please try again later."]_

### Error Message Style

_[How errors should sound. e.g., "Name the problem specifically. Suggest a concrete next step. Never blame the user. Never use 'Oops.'"]_

### CTA Style

_[How calls to action should read. e.g., "Action-specific verbs tied to what actually happens: 'Create project', 'Send invoice', 'Download report'. Never 'Get Started' or 'Learn More'."]_

## Naming Conventions

Project-specific naming patterns that agents must follow. Generic names are banned unless explicitly permitted here.

**Module naming:** _[e.g., "Domain-verb pattern: `payment-processing`, `invoice-generation`. Never `utils`, `helpers`, `misc`."]_

**Route naming:** _[e.g., "Resource-oriented: `/projects/:id/tasks`. Never `/api/v1/getData`."]_

**Component naming:** _[e.g., "Purpose-first: `InvoiceLineItem`, `ProjectTimeline`. Never `Card`, `Widget`, `Item`."]_

**Variable/function naming:** _[Conventions specific to this project's domain language]_

## Architectural Divergence (Optional)

Technology choices that deliberately differ from the common default, with rationale from research.

| Decision | Default (avoided) | Chosen Alternative | Rationale |
|----------|-------------------|-------------------|-----------|
| _[e.g., "Color space"]_ | _[sRGB hex]_ | _[OKLCH]_ | _[Perceptual uniformity, better gradients]_ |
| _[e.g., "State management"]_ | _[Redux]_ | _[Zustand]_ | _[Research finding: simpler API, smaller bundle for this scope]_ |
