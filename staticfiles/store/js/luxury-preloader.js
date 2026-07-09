/**
 * Luxury Preloader Animation
 * Cicada Rise - Premium Fashion Brand
 * GSAP-powered elegant loading experience
 */

(function() {
  if (typeof gsap === 'undefined') return;

  const preloader = document.getElementById('preloader');
  const logo = document.querySelector('.preloader-logo');
  const dots = document.querySelectorAll('.dot');

  if (!preloader || !logo) return;

  // Create main timeline
  const timeline = gsap.timeline({ defaults: { ease: 'power2.inOut' } });

  // Phase 1: Logo fades in and scales up (0-0.8s)
  timeline.to(
    logo,
    {
      opacity: 1,
      scale: 1,
      duration: 0.8,
      ease: 'power2.out'
    },
    0
  );

  // Phase 2: Apply floating animation to logo (starts at 0.4s)
  timeline.call(() => {
    logo.classList.add('animated');
  }, [], 0.4);

  // Phase 3: Dots fade in (0.4-0.8s)
  timeline.to(
    dots,
    {
      opacity: 0.3,
      duration: 0.4,
      stagger: 0.1
    },
    0.4
  );

  // Wait for page to fully load or timeout after 3 seconds
  let preloaderComplete = false;

  const completePreloader = () => {
    if (preloaderComplete) return;
    preloaderComplete = true;

    // Timeline for exit animation
    const exitTimeline = gsap.timeline();

    // Fade out dots
    exitTimeline.to(
      dots,
      {
        opacity: 0,
        duration: 0.3,
        stagger: 0.05
      },
      0
    );

    // Fade out logo
    exitTimeline.to(
      logo,
      {
        opacity: 0,
        duration: 0.4
      },
      0.1
    );

    // Fade out preloader background
    exitTimeline.to(
      preloader,
      {
        opacity: 0,
        duration: 0.5,
        ease: 'power2.inOut',
        onComplete: () => {
          preloader.classList.add('complete');
          preloader.style.display = 'none';
        }
      },
      0.2
    );
  };

  // Trigger on window load
  window.addEventListener('load', completePreloader);

  // Auto-hide after 4 seconds (safety timeout)
  setTimeout(() => {
    completePreloader();
  }, 4000);
})();
