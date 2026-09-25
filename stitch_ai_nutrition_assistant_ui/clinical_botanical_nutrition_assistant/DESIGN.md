---
name: Clinical Botanical Nutrition Assistant
colors:
  surface: '#10141a'
  surface-dim: '#10141a'
  surface-bright: '#353940'
  surface-container-lowest: '#0a0e14'
  surface-container-low: '#181c22'
  surface-container: '#1c2026'
  surface-container-high: '#262a31'
  surface-container-highest: '#31353c'
  on-surface: '#dfe2eb'
  on-surface-variant: '#bfc9c1'
  inverse-surface: '#dfe2eb'
  inverse-on-surface: '#2d3137'
  outline: '#8a938c'
  outline-variant: '#404943'
  surface-tint: '#96d4b4'
  primary: '#97d4b4'
  on-primary: '#003825'
  primary-container: '#7cb89a'
  on-primary-container: '#054932'
  inverse-primary: '#2e694f'
  secondary: '#bbc8d5'
  on-secondary: '#25323c'
  secondary-container: '#3c4853'
  on-secondary-container: '#aab7c3'
  tertiary: '#b5ccc0'
  on-tertiary: '#20342c'
  tertiary-container: '#9ab1a5'
  on-tertiary-container: '#30443b'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#b2f0cf'
  primary-fixed-dim: '#96d4b4'
  on-primary-fixed: '#002114'
  on-primary-fixed-variant: '#115139'
  secondary-fixed: '#d7e4f1'
  secondary-fixed-dim: '#bbc8d5'
  on-secondary-fixed: '#101d26'
  on-secondary-fixed-variant: '#3c4853'
  tertiary-fixed: '#d0e8db'
  tertiary-fixed-dim: '#b5ccc0'
  on-tertiary-fixed: '#0b1f18'
  on-tertiary-fixed-variant: '#374b42'
  background: '#10141a'
  on-background: '#dfe2eb'
  surface-variant: '#31353c'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: DM Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: '0'
  body-md:
    fontFamily: DM Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: '0'
  body-sm:
    fontFamily: DM Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.005em
  label-md:
    fontFamily: DM Sans
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: DM Sans
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.04em
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: '0'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-desktop: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style

This design system establishes a clinical, trustworthy food science aesthetic that pairs biochemical precision with botanical clarity. Designed for a dark-first nutritional intelligence environment, the visual language avoids neon hues, sci-fi glows, or decorative crypto-style widgets in favor of disciplined data density, quiet restraint, and medical-grade legibility.

The mood reflects an advanced diagnostic laboratory: calm, sterile, yet organic. It instills absolute confidence in dietary analysis, macronutrient modeling, and metabolic health insights. Structural surfaces rely on deep mineral tones, quiet hairline borders, and muted botanical accents that evoke fresh herbal extracts, natural specimens, and laboratory glassware.

## Colors

The palette is engineered specifically for deep-focus clinical review, prioritizing visual comfort and low ocular fatigue during long analytical sessions.

- **Background Archetypes**: 
  - Base canvas: `#0C0F12` (deep obsidian carbon).
  - Primary work surfaces / cards: `#13171D` (cool lab slate).
  - Elevated containers / chat bubbles: `#181D24`.
  - Active interactive layers & floating popovers: `#1F2630`.
- **Accent Systems**:
  - Primary Botanical Accent: `#7CB89A` (muted medicinal sage), hovering to `#92C6AC`.
  - Tonal Botanical Base: `#172B23` (subtle botanical wash used behind focused metrics, citations, and system badges).
- **Text & Metadata**:
  - Primary Content: `#F0F4F2` (mineral off-white for crisp readability).
  - Secondary / Supporting Metadata: `#8F9CA8` (neutral clinical slate for timestamps, source indices, and axis labels).
  - Tertiary / Inactive: `#5A6675` (disabled states, unselected tabs).
- **Dividers & Structural Rules**:
  - Hairline Borders: `#262E3B` or `rgba(255, 255, 255, 0.08)`. Never use thick solid borders or drop glows.

## Typography

The typographic hierarchy combines structural clarity with clinical legibility:

- **Headings (Plus Jakarta Sans)**: Used for view titles, panel headers, and nutritional summary titles. Semi-bold weight (`600`) provides a sturdy, scientific posture without appearing playful or aggressive.
- **Body & Data (DM Sans)**: Used for all conversational exchanges, metabolic breakdowns, nutrient references, and documentation. Delivers neutral geometry and balanced horizontal proportion for numerical arrays.
- **Micro-Labels & Technical Annotations (JetBrains Mono & DM Sans)**: JetBrains Mono is strictly reserved for quantitative values, units of measure (`mg`, `kcal`, `µg`), biochemical markers, and reference tokens.

## Layout & Spacing

The desktop architecture adopts an asymmetrical dual-pane workspace optimized for clinical review:
- **Desktop (>= 1200px)**: A 65/35 split view.
  - **Left Workstation (65%)**: Streamlined, linear conversational interface featuring query inputs, nutrient timeline logs, and synthesized AI dietary outputs.
  - **Right Inspector Panel (35%)**: Anchored sidebar displaying peer-reviewed scientific citations, biochemical mechanism cards, USDA/EFSA nutritional database verification, and ingredient cross-analyses.
- **Tablet / Small Desktop (768px - 1199px)**: Inspector collapses into a full-height slide-over drawer triggered by inline citation chips.
- **Mobile (< 768px)**: Stacked single-column view with bottom sheet expansion for source validation and nutrient breakdowns.

Internal component rhythm follows a rigid 4px/8px incremental scale (`space-xs` to `space-xl`), ensuring compact density appropriate for professional clinical tools without feeling claustrophobic.

## Elevation & Depth

Visual separation avoids heavy, muddy drop shadows or radiant neon glows. Instead, physical hierarchy is constructed through **tonal stratification and hairline borders**:

1. **Canvas (Base level 0)**: `#0C0F12`, completely unbordered.
2. **Main Cards & Structural Columns (Level 1)**: `#13171D` with a crisp 1px perimeter border of `#262E3B`.
3. **Interactive & Elevated Containers (Level 2)**: `#181D24` with a 1px border of `rgba(255, 255, 255, 0.08)` and an ultra-subtle, non-directional shadow: `0 4px 16px rgba(0, 0, 0, 0.35)`.
4. **Popovers, Dropdowns, & Modals (Level 3)**: `#1F2630` with `1px solid rgba(124, 184, 154, 0.2)` highlighting context focus, supported by `0 12px 32px rgba(0, 0, 0, 0.6)`.

Surfaces never use vibrant glassmorphic blurs; light attenuation is matte and controlled.

## Shapes

The design uses controlled geometric rounding (Level 2).
- Standard UI containers, cards, and input fields: `8px` (`0.5rem`).
- Elevated modal containers and master analytical panels: `12px` (`0.75rem`).
- Citation badges, scientific status pills, and action chips: `9999px` (pill-shaped) for contrast against structural square grids.
- Icon containers and technical indicators: `6px`.

## Components

### Buttons
- **Primary Action**: Solid `#7CB89A` background with `#0C0F12` bold text. On hover: `#92C6AC`. On active: `#6DA688`. Height: 36px (compact) to 40px (regular). Radius: 8px. Padding: 0 16px.
- **Secondary / Ghost**: Background: transparent; border: `1px solid #262E3B`; text: `#F0F4F2`. On hover: background `#181D24`, border `rgba(255, 255, 255, 0.15)`.
- **Botanical Subtle**: Background: `#172B23`; border: `1px solid rgba(124, 184, 154, 0.25)`; text: `#7CB89A`.

### Input Fields & Prompt Composer
- Background: `#13171D`; border: `1px solid #262E3B`; text: `#F0F4F2`; placeholder: `#5A6675`.
- Focus state: border `1px solid #7CB89A`, subtle outer ring `0 0 0 1px rgba(124, 184, 154, 0.25)`.
- Chat input includes docked auxiliary actions: token counter, file attachment trigger (lab reports, blood work PDFs), and nutrient filter selector.

### Citation Chips & Reference Tags
- Inline text citations within chat responses use pill indicators: `#172B23` background, `#7CB89A` text, `1px solid rgba(124, 184, 154, 0.3)`, font: JetBrains Mono (11px).
- Clicking an inline citation updates and focuses the scientific inspector panel in the 35% side rail.

### Chat Stream Bubbles
- **User Message**: Aligned right or distinct; background `#181D24`; border: `1px solid #262E3B`; text: `#F0F4F2`.
- **System / AI Nutritionist**: Full-width or aligned left; clean minimal background `#13171D` (or borderless on canvas `#0C0F12`); structured with systematic sub-headers, quantitative metric grids, and scientific takeaway lists.

### Nutritional Data Cards & Source Panels
- Structured card with a 1px border (`#262E3B`), background `#13171D`.
- Card header features a clinical monospace tag (e.g., `REF: USDA-SR28`, `PMID: 34187532`) and a status dot (`#7CB89A` for verified, `#D9A74A` for observational data).
- Data points arranged in high-density horizontal metric strips: label in `#8F9CA8`, numeric value in `#F0F4F2` JetBrains Mono.