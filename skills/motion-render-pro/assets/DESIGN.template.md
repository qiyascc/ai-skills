# DESIGN

Read this before touching any scene. Change it only when the user changes the look.

## Format

- Canvas: 1080×1920, [fps] fps, [duration] s
- Edge margin: 75 px (0.11 W); Instagram UI zones: top ~250 px, bottom ~420 px, right ~120 px

## Palette

| Role | Hex |
|---|---|
| Background | [#hex, gradient or texture] |
| Hero | [#hex] |
| Accent (one key thing per screen) | [#hex] |
| Text | [#hex] |
| Light / glow | [rgba] |

## Type

- Display: [family, weight], used for [hero words, numbers]
- Support: [family, weight], used for [labels, small copy]
- Font files: [paths registered with GlobalFonts.registerFromPath]

## Hero object

[What it is, size relative to W, material, every form it takes in the film]

## Motion vocabulary

- Style: [UI physics (pop, overshoot, squash) or real physics (gravity, one rebound)], never both
- Curves: [E.start for ..., E.drop for ..., E.camera for camera moves, pop for badges]
- Motion blur: shutter 0.5, 8 sub-frames, 16 to 32 on whips
- Entrances and exits: [move, scale from cause, mask roll, iris]; no fades except light

## Camera

[Zoom factors per shot, push/pull rules, depth layers]

## Ban list

[emoji, generic particles, pulse rings, dashed lines, outline icons, invented logos, faces, ...]
