/**
 * CICADA RISE - ULTRA-PREMIUM PRELOADER SYSTEM
 * 
 * Luxury Fashion Brand Loading Animation
 * Designed for a high-end e-commerce experience
 * 
 * ANIMATION BREAKDOWN:
 * ======================
 * 
 * 1. INITIALIZATION (0-1.2s)
 *    - Frosted ivory background with subtle blur effect
 *    - SVG container centered on viewport
 * 
 * 2. STROKE DRAWING (0-0.8s)
 *    - Outer C hexagonal outline draws smoothly
 *    - Uses SVG stroke-dasharray animation
 *    - Elegant curve motion with power1.inOut easing
 * 
 * 3. INNER OUTLINE (0.3-0.9s)
 *    - Inner C outline draws (slightly delayed)
 *    - Complements the outer shape
 *    - Same smooth stroke animation
 * 
 * 4. LEAF ELEMENT (0.7-1.2s)
 *    - Leaf fades in and scales up from 0.85 to 1
 *    - Soft glow filter applied (rgba(176,138,87,0.35))
 *    - Creates focal point inside the icon
 * 
 * 5. LOADING RING (1.2-5.0s)
 *    - Circular progress ring appears around icon
 *    - Base ring in muted beige (#DCCDB9)
 *    - Progress highlight in champagne gold (#B08A57)
 * 
 * 6. RING ANIMATION (1.2-5.0s)
 *    - Clockwise rotation (360°) over 2.5s
 *    - Continuous loop using GSAP repeat: -1
 *    - Glowing highlight travels along ring
 * 
 * 7. COMPLETION SHIMMER (2.8s)
 *    - Leaf receives subtle golden shimmer
 *    - Entire preloader fades upward
 *    - Opacity 0, Y position -30px
 *    - Completes in 0.8s with smooth easing
 * 
 * 8. AUTO-HIDE FALLBACK (5.0s)
 *    - Safety mechanism if page doesn't fully load
 *    - Prevents preloader from blocking content
 * 
 * VISUAL SPECIFICATIONS:
 * ======================
 * - Logo Color: #3E0202 (deep maroon)
 * - Background: rgba(248,244,239,0.94) with blur(12px)
 * - Base Ring: #DCCDB9 (muted beige)
 * - Progress: #B08A57 (champagne gold)
 * - Glow: rgba(176,138,87,0.35)
 * - Icon Size: 140x140px (responsive to 120px on mobile)
 * - Stroke Width: 1.8px (logo), 1.5px (leaf), 1.2px (ring)
 * - Total Duration: ~3.6s (design phase) + ongoing ring animation
 * 
 * PERFORMANCE:
 * ======================
 * - SVG-based (lightweight, scalable)
 * - GSAP animations (60 FPS)
 * - No rasterization or unnecessary repaints
 * - Smooth on desktop and mobile devices
 * - Auto-cleanup after animation completion
 * 
 * FILES:
 * ======================
 * - /store/static/store/js/preloader.js (GSAP animation logic)
 * - /store/static/store/css/preloader.css (styling)
 * - /store/templates/store/base.html (HTML structure)
 * 
 * BROWSER SUPPORT:
 * ======================
 * - Chrome 90+
 * - Firefox 88+
 * - Safari 14+
 * - Edge 90+
 * - Mobile browsers (iOS Safari, Chrome Mobile)
 * 
 * EASING FUNCTIONS:
 * ======================
 * - Stroke Draw: power1.inOut (smooth, elegant)
 * - Scale/Fade: power2.out (soft entrance)
 * - Ring Rotate: linear (constant, hypnotic)
 * - Fade Out: power2.inOut (smooth exit)
 */
