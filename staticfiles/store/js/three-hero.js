// Three.js Luxury Hero Particle System
document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.getElementById("three-canvas");
    if (!canvas) return;

    let scene, camera, renderer, particles;
    let mouseX = 0, mouseY = 0;
    let windowHalfX = window.innerWidth / 2;
    let windowHalfY = window.innerHeight / 2;

    const init = () => {
        // Create Scene & Camera
        scene = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 1, 2000);
        camera.position.z = 1000;

        // Create Particle Geometry
        const geometry = new THREE.BufferGeometry();
        const vertices = [];

        // 600 floating golden dust particles
        for (let i = 0; i < 600; i++) {
            const x = Math.random() * 2000 - 1000;
            const y = Math.random() * 2000 - 1000;
            const z = Math.random() * 2000 - 1000;
            vertices.push(x, y, z);
        }

        geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));

        // Create canvas particle texture (subtle soft circular particle)
        const size = 16;
        const pCanvas = document.createElement('canvas');
        pCanvas.width = size;
        pCanvas.height = size;
        const ctx = pCanvas.getContext('2d');
        const grad = ctx.createRadialGradient(size/2, size/2, 0, size/2, size/2, size/2);
        grad.addColorStop(0, 'rgba(200, 161, 106, 1)'); // Brand Gold
        grad.addColorStop(0.3, 'rgba(200, 161, 106, 0.6)');
        grad.addColorStop(1, 'rgba(200, 161, 106, 0)');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, size, size);

        const texture = new THREE.CanvasTexture(pCanvas);

        // Material config
        const material = new THREE.PointsMaterial({
            size: 6,
            map: texture,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
            transparent: true,
            opacity: 0.85
        });

        particles = new THREE.Points(geometry, material);
        scene.add(particles);

        // WebGL Renderer Setup
        renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.setSize(canvas.clientWidth, canvas.clientHeight);

        // Listeners
        document.addEventListener('mousemove', onDocumentMouseMove);
        window.addEventListener('resize', onWindowResize);
    };

    const onDocumentMouseMove = (event) => {
        mouseX = event.clientX - windowHalfX;
        mouseY = event.clientY - windowHalfY;
    };

    const onWindowResize = () => {
        windowHalfX = window.innerWidth / 2;
        windowHalfY = window.innerHeight / 2;
        camera.aspect = canvas.clientWidth / canvas.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    };

    const animate = () => {
        requestAnimationFrame(animate);
        render();
    };

    const render = () => {
        // Slow rotation of particles
        const time = Date.now() * 0.00003;
        particles.rotation.y = time * 0.5;
        particles.rotation.x = time * 0.25;

        // Camera responds slowly to mouse position
        camera.position.x += (mouseX * 0.25 - camera.position.x) * 0.05;
        camera.position.y += (-mouseY * 0.25 - camera.position.y) * 0.05;
        camera.lookAt(scene.position);

        renderer.render(scene, camera);
    };

    // Initialize with try-catch block for resilience
    try {
        init();
        animate();
    } catch (e) {
        console.warn("Three.js initialization failed: ", e);
    }
});
