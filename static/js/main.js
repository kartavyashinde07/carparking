const html = document.documentElement;
const canvas = document.getElementById("hero-lightpass");

// ❗ SAFETY CHECK
if (!canvas) {
    console.warn("Canvas element not found on this page. Stopping animation script.");
}

// 🚀 PERFORMANCE UPGRADE 1: { alpha: false }
const context = canvas ? canvas.getContext("2d", { alpha: false }) : null;

// UI Elements
const loginWrapper = document.getElementById("login-wrapper");
const scrollIndicator = document.getElementById("scroll-indicator");
const heroText = document.getElementById("hero-text");
const carThumb = document.getElementById("car-thumb");

// CONFIG
const frameCount = 192;
const images = [];

// IMAGE PATH (Pads index: 1 -> "0001", 12 -> "0012")
const imgPath = (index) => `/static/assets/car_sequence/${index.toString().padStart(4, '0')}.jpg`;

// ✅ PRELOAD IMAGES & ASYNC DECODE
function preloadImages() {
    for (let i = 1; i <= frameCount; i++) {
        const img = new Image();
        img.src = imgPath(i);
        images.push(img);
        
        // 🚀 PERFORMANCE UPGRADE 2: Async Decoding
        img.decode().catch(() => {
            // Silently ignore decode errors if an image is missing
        });
        
        // Draw the very first frame as soon as it is ready
        if (i === 1) {
            img.onload = () => {
                updateImage(0);
            };
        }
    }
}

// ✅ SET CANVAS SIZE (Covers the whole screen)
function setCanvasSize() {
    if (!canvas) return;
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}

// ✅ DRAW IMAGE (Mimics CSS object-fit: cover)
function updateImage(index) {
    if (!context || !images[index]) return;

    const img = images[index];

    // Wait until this specific image is actually loaded
    if (!img.complete) return;

    // Calculate aspect ratio to cover the screen without stretching the car
    const scale = Math.max(
        canvas.width / img.width,
        canvas.height / img.height
    );

    const newWidth = img.width * scale;
    const newHeight = img.height * scale;

    // Center the image
    const x = (canvas.width - newWidth) / 2;
    const y = (canvas.height - newHeight) / 2;

    // We don't need clearRect() anymore because {alpha: false} guarantees we just overwrite the old pixels!
    context.drawImage(img, x, y, newWidth, newHeight);
}

// 🚀 PERFORMANCE UPGRADE 3: Scroll Throttling
let ticking = false; 

function handleScroll() {
    // If the browser is already busy drawing a frame, ignore this scroll event
    if (!ticking) {
        window.requestAnimationFrame(() => {
            performScrollMath();
            ticking = false; 
        });
        ticking = true; 
    }
}

// ✅ SCROLL MATH
function performScrollMath() {
    const scrollTop = html.scrollTop;
    const maxScrollTop = html.scrollHeight - window.innerHeight;

    // Prevent division by zero if page hasn't applied CSS height yet
    if (maxScrollTop <= 0) return;

    const fraction = scrollTop / maxScrollTop;

    // Determine which image to show (Index 0 to 191)
    const frameIndex = Math.min(
        frameCount - 1,
        Math.floor(fraction * frameCount)
    );

    updateImage(frameIndex);

    // 💨 TEXT FADE (Fades out completely in the first 20% of the scroll)
    if (heroText) {
        heroText.style.opacity = Math.max(0, 1 - (fraction * 5));
    }

    // 🚗 CAR THUMB MOVE
    if (carThumb) {
        carThumb.style.top = `${fraction * (window.innerHeight - 40)}px`;
    }

    // 🔐 LOGIN VISIBILITY
    if (loginWrapper && scrollIndicator) {
        if (fraction > 0.98) {
            loginWrapper.classList.add("visible");
            scrollIndicator.style.opacity = "0";
        } else {
            loginWrapper.classList.remove("visible");
            scrollIndicator.style.opacity = "1";
        }
    }
}

// ✅ RESIZE HANDLER
let lastWidth = window.innerWidth;
let lastHeight = window.innerHeight;

function handleResize() {
    // Only redraw if the actual dimensions changed (fixes mobile browser address bar glitches)
    if (window.innerWidth !== lastWidth || window.innerHeight !== lastHeight) {
        lastWidth = window.innerWidth;
        lastHeight = window.innerHeight;
        
        setCanvasSize();
        
        // ❗ CRITICAL FIX: Redraw the *current* frame when resizing, so the screen doesn't go blank
        const maxScrollTop = html.scrollHeight - window.innerHeight;
        const fraction = maxScrollTop > 0 ? html.scrollTop / maxScrollTop : 0;
        const frameIndex = Math.min(frameCount - 1, Math.floor(fraction * frameCount));
        
        updateImage(frameIndex);
    }
}

// ✅ INITIALIZE SAFELY
window.addEventListener("DOMContentLoaded", () => {
    if (!canvas) return; // Stop script if not on the login page

    setCanvasSize();
    preloadImages(); // This will trigger updateImage(0) automatically once ready

    // Use the passive flag to tell the browser this scroll event won't block the page
    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("resize", handleResize);
});