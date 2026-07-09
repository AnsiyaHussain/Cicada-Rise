// GSAP Animations and Interactive Elements
document.addEventListener("DOMContentLoaded", () => {
    
    // 1. GSAP Luxury Preloader
    const preloader = document.getElementById("preloader");
    if (preloader) {
        const tl = gsap.timeline({
            onComplete: () => {
                preloader.style.display = "none";
                document.body.style.overflow = "auto";
                
                // Trigger hero text animations after loader finishes
                animateHeroContent();
            }
        });

        // Set body overflow hidden while loading
        document.body.style.overflow = "hidden";

        tl.to(".loader-logo", { opacity: 1, y: 0, duration: 0.8, ease: "power2.out" })
          .to(".loader-progress", { left: "0%", duration: 1.2, ease: "power1.inOut" })
          .to("#preloader", { opacity: 0, y: "-100%", duration: 0.6, ease: "power2.in" }, "+=0.3");
    } else {
        animateHeroContent();
    }

    // 2. Hero Content Animations
    function animateHeroContent() {
        if (document.querySelector(".hero-content")) {
            gsap.from(".hero-content h1", {
                opacity: 0,
                y: 50,
                duration: 1,
                ease: "power3.out"
            });
            
            gsap.from(".hero-content p", {
                opacity: 0,
                y: 30,
                duration: 1,
                delay: 0.3,
                ease: "power3.out"
            });
            
            gsap.from(".hero-content .btn", {
                opacity: 0,
                y: 20,
                duration: 0.8,
                delay: 0.5,
                ease: "power3.out"
            });
        }
    }

    // 3. Floating Cicada Bobbing Animation
    const cicada = document.querySelector(".floating-cicada");
    if (cicada) {
        gsap.to(cicada, {
            y: "-10px",
            duration: 2,
            repeat: -1,
            yoyo: true,
            ease: "sine.inOut"
        });
    }

    // 4. Scroll Animations (ScrollTrigger)
    if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
        gsap.registerPlugin(ScrollTrigger);

        // Product cards fade-in grid
        gsap.utils.toArray('.product-card').forEach((card) => {
            gsap.from(card, {
                scrollTrigger: {
                    trigger: card,
                    start: 'top 90%',
                    toggleActions: 'play none none none'
                },
                opacity: 0,
                y: 40,
                duration: 0.8,
                ease: 'power2.out'
            });
        });

        // Story section elements fade-in
        if (document.querySelector('.story-wrapper')) {
            gsap.from('.story-image', {
                scrollTrigger: {
                    trigger: '.story-wrapper',
                    start: 'top 80%'
                },
                opacity: 0,
                x: -50,
                duration: 1,
                ease: 'power2.out'
            });
            
            gsap.from('.story-text', {
                scrollTrigger: {
                    trigger: '.story-wrapper',
                    start: 'top 80%'
                },
                opacity: 0,
                x: 50,
                duration: 1,
                ease: 'power2.out'
            });
        }
    }

    // 5. Dynamic Toast Notifications
    window.showToast = (message, type = 'success') => {
        // Remove existing toasts if any
        const existingToast = document.querySelector('.custom-toast');
        if (existingToast) existingToast.remove();

        const toast = document.createElement('div');
        toast.className = `custom-toast alert alert-${type} px-4 py-3 shadow-lg`;
        toast.style.cssText = `
            position: fixed;
            bottom: 85px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            z-index: 9999;
            opacity: 0;
            border-radius: 0;
            border-left: 4px solid var(--gold);
            background: var(--white);
            color: var(--primary);
            font-size: 0.9rem;
            transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
        `;
        toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle text-success' : 'fa-exclamation-circle text-danger'} me-2"></i> ${message}`;
        document.body.appendChild(toast);

        // GSAP animate toast entrance
        gsap.to(toast, {
            opacity: 1,
            y: 0,
            duration: 0.5,
            onComplete: () => {
                setTimeout(() => {
                    gsap.to(toast, {
                        opacity: 0,
                        y: 100,
                        duration: 0.5,
                        onComplete: () => toast.remove()
                    });
                }, 3000);
            }
        });
    };

    // 6. HTMX Event Bindings for Navbar Count Badges
    document.body.addEventListener("updateCartCount", (e) => {
        const counts = document.querySelectorAll(".cart-count-badge");
        counts.forEach(badge => {
            badge.innerText = e.detail.value;
            badge.style.display = e.detail.value > 0 ? "flex" : "none";
        });
        showToast("Cart updated successfully!");
    });

    document.body.addEventListener("updateWishlistCount", (e) => {
        const counts = document.querySelectorAll(".wishlist-count-badge");
        counts.forEach(badge => {
            badge.innerText = e.detail.value;
            badge.style.display = e.detail.value > 0 ? "flex" : "none";
        });
        showToast("Wishlist updated!");
    });

    document.body.addEventListener("reloadCart", () => {
        // Refresh page to update cart totals or request new cart HTML
        setTimeout(() => {
            window.location.reload();
        }, 300);
    });
});
