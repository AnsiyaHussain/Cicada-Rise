/**
 * Ultra-Premium Preloader Animation
 * Cicada Rise - Luxury Women's Fashion
 * GSAP-based stroke animation with loading ring
 */

(function() {
  if (typeof gsap === 'undefined') return;

  const preloader = document.getElementById('preloader');
  const svgPaths = {
    outerC: document.getElementById('outer-c-path'),
    innerC: document.getElementById('inner-c-path'),
    leaf: document.getElementById('leaf-element'),
    loadingRing: document.getElementById('loading-ring'),
    highlight: document.getElementById('ring-highlight')
  };

  if (!preloader || !svgPaths.outerC) return;

  // Set initial stroke properties for drawing animation
  [svgPaths.outerC, svgPaths.innerC].forEach(path => {
    if (path) {
      const length = path.getTotalLength();
      path.style.strokeDasharray = length;
      path.style.strokeDashoffset = length;
    }
  });

  // Leaf initial state
  if (svgPaths.leaf) {
    svgPaths.leaf.style.opacity = '0';
    svgPaths.leaf.style.transform = 'scale(0.85)';
  }

  // Loading ring initial state
  if (svgPaths.loadingRing) {
    svgPaths.loadingRing.style.opacity = '0';
  }
  if (svgPaths.highlight) {
    svgPaths.highlight.style.opacity = '0';
  }

  // Create GSAP timeline
  const timeline = gsap.timeline({ defaults: { ease: 'power2.inOut' } });

  // Phase 1: Draw outer C outline (0.8s)
  if (svgPaths.outerC) {
    timeline.to(
      svgPaths.outerC,
      {
        strokeDashoffset: 0,
        duration: 0.8,
        ease: 'power1.inOut'
      },
      0
    );
  }

  // Phase 2: Draw inner C outline (0.6s, starts at 0.3s)
  if (svgPaths.innerC) {
    timeline.to(
      svgPaths.innerC,
      {
        strokeDashoffset: 0,
        duration: 0.6,
        ease: 'power1.inOut'
      },
      0.3
    );
  }

  // Phase 3: Fade and scale in leaf with glow (0.5s, starts at 0.7s)
  if (svgPaths.leaf) {
    timeline.to(
      svgPaths.leaf,
      {
        opacity: 1,
        transform: 'scale(1)',
        duration: 0.5,
        ease: 'power2.out'
      },
      0.7
    );
  }

  // Phase 4: Appear loading ring (0.3s, at 1.2s)
  if (svgPaths.loadingRing) {
    timeline.to(
      svgPaths.loadingRing,
      {
        opacity: 1,
        duration: 0.3,
        ease: 'power2.out'
      },
      1.2
    );
  }

  // Phase 5: Animate loading ring clockwise (starts at 1.2s, continuous)
  if (svgPaths.loadingRing) {
    timeline.to(
      svgPaths.loadingRing,
      {
        rotation: 360,
        duration: 2.5,
        ease: 'linear',
        repeat: -1
      },
      1.2
    );
  }

  // Phase 6: Animate highlight along the ring (starts at 1.2s)
  if (svgPaths.highlight) {
    timeline.to(
      svgPaths.highlight,
      {
        opacity: 1,
        duration: 0.2,
        ease: 'power2.out'
      },
      1.2
    );

    timeline.to(
      svgPaths.highlight,
      {
        rotation: 360,
        duration: 2.5,
        ease: 'linear',
        repeat: -1,
        transformOrigin: '50% 50%'
      },
      1.2,
      '<'
    );
  }

  // Phase 7: Shimmer leaf effect and fade out (at 2.8s)
  timeline.call(() => {
    // Leaf shimmer
    if (svgPaths.leaf) {
      gsap.to(svgPaths.leaf, {
        opacity: 1.2,
        duration: 0.2,
        yoyo: true,
        repeat: 1,
        ease: 'power2.out'
      });
    }

    // Fade out entire preloader
    gsap.to(preloader, {
      opacity: 0,
      y: -30,
      duration: 0.8,
      ease: 'power2.inOut',
      onComplete: () => {
        preloader.style.display = 'none';
        preloader.style.pointerEvents = 'none';
      }
    });
  }, 2.8);

  // Fallback: Auto-hide after 5 seconds
  setTimeout(() => {
    if (preloader.style.display !== 'none') {
      gsap.to(preloader, {
        opacity: 0,
        y: -30,
        duration: 0.6,
        ease: 'power2.inOut',
        onComplete: () => {
          preloader.style.display = 'none';
        }
      });
    }
  }, 5000);
})();
