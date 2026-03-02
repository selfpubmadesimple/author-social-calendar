# Author Social Calendar App - Design Guidelines

## Design Approach

**Reference-Based: Canva-Inspired Modern SaaS**

Drawing from Canva's design language: clean layouts, generous whitespace, modern typography, vibrant professional aesthetic. Adapting for productivity-focused content planning with Linear's efficiency and Notion's information architecture.

**Core Principles:**
- Clean, uncluttered interfaces with purposeful spacing
- Professional yet approachable for creative professionals
- Information hierarchy through typography and layout, not excessive decoration
- Functional beauty - every element serves the user's workflow

---

## Typography System

**Font Family:** Inter (primary) + DM Sans (headings)
- Headings: DM Sans - Bold (text-2xl to text-4xl)
- Subheadings: DM Sans - Semibold (text-lg to text-xl)
- Body: Inter - Regular (text-sm to text-base)
- UI Labels: Inter - Medium (text-xs to text-sm)
- Calendar dates: DM Sans - Medium (text-sm)

---

## Layout & Spacing

**Spacing Primitives:** Tailwind units of 3, 4, 6, 8, 12
- Component padding: p-4 to p-6
- Section spacing: gap-6 to gap-8
- Card spacing: p-4 internal, gap-4 between items
- Calendar cells: p-3

**Grid Structure:**
- Dashboard: Sidebar (280px fixed) + Main content (flex-1)
- Calendar grid: 7 columns (days of week)
- Instagram preview: 3x3 grid (aspect-square)
- Content cards: Grid with gap-4

---

## Component Library

### Navigation Sidebar
- Fixed left sidebar (280px, full height)
- Logo/brand at top (p-6)
- Navigation items with icons (p-3, gap-3)
- Active state: Subtle background treatment
- Bottom section: User profile, settings

### Calendar Planner View
- Month header: Month/year selector with navigation arrows
- Days of week row: Sticky header, uppercase labels (text-xs, font-medium)
- Date cells: Rounded corners (rounded-lg), min-height for content
- Post previews in cells: Thumbnail image (w-full, aspect-video, rounded), title (text-xs, truncate), time indicator
- Multi-post cells: Stack with "+2 more" indicator
- Empty states: Dashed border, "+ Add post" button

### Instagram Grid Preview Panel
- Right panel or modal (420px width)
- Header: "Instagram Preview" + profile info mock
- 3x3 grid: aspect-square tiles, gap-1 (Instagram's minimal gap)
- Post tiles: Full-bleed images, hover overlay showing caption preview
- Grid arrangement: Shows latest 9 posts in chronological order
- Navigation: Scroll to see older posts beyond grid

### Post Creation/Edit Interface
- Two-column layout: Editor (60%) + Preview (40%)
- Editor section: DALL-E prompt input (rounded-lg, p-4), generated image display, caption editor (textarea with formatting), platform toggles
- Preview section: Live platform-specific previews (Instagram, Facebook, etc.)
- Action buttons: Generate, Schedule, Save Draft (fixed bottom bar)

### Content Cards
- Rounded corners (rounded-xl)
- Padding: p-4
- Image thumbnails: aspect-video, rounded-lg, mb-3
- Title: text-base, font-semibold, mb-2
- Metadata: text-xs, flex items with gaps
- Actions: Icon buttons in top-right corner

---

## Key Interactions

**Calendar Interactions:**
- Click date cell: Opens post creation modal
- Drag and drop: Reschedule posts between dates
- Click existing post: Opens edit view
- Hover post preview: Shows full caption + engagement preview

**Instagram Grid:**
- Grid updates in real-time as posts are scheduled
- Click tile: Opens full post detail with analytics
- Reorder capability: Drag tiles to rearrange grid (affects posting schedule)

**Content Generation:**
- Inline DALL-E generation with loading states
- Regenerate button with variations
- AI caption suggestions appear as chips to insert

---

## Icons

**Library:** Heroicons (outline for default, solid for active states)

Essential icons:
- Navigation: Calendar, Grid, Sparkles (AI), Image, Settings
- Actions: Plus, Edit, Trash, Copy, Share
- Calendar: ChevronLeft/Right, Clock
- Posts: Photo, Caption, Heart, Comment

---

## Images

**Hero Section:** None - This is a dashboard application, not a marketing site. Application opens directly to the calendar view.

**Post Thumbnails:**
- All user-generated DALL-E images
- Aspect ratios: 1:1 (Instagram), 16:9 (general), 4:5 (portrait)
- Placeholder: Subtle gradient with icon when no image

**Instagram Preview:**
- Use actual generated post images in 1:1 aspect ratio
- Maintain consistent sizing across grid

---

## Dashboard Layout Structure

1. **Top Bar:** App name/logo (left), search, notification bell, user avatar (right) - h-16, border-bottom
2. **Main Container:** Flex row
3. **Sidebar:** Fixed 280px, navigation tree, bottom user section
4. **Content Area:** Flex-1, p-6 to p-8
5. **Calendar View:** Full-width grid within content area
6. **Preview Panel:** Slide-in from right (420px) or inline right column for Instagram grid