/**
 * main.js  –  Utility helpers for the Login page.
 *
 * The scroll-based cinematic animation has been removed.
 * The hero is now a static full-screen background (car_sequence/0192.jpg).
 */

// ── Password visibility toggle ──────────────────────────────────────────────
function togglePassword() {
    const pass = document.getElementById('password');
    if (!pass) return;
    pass.type = pass.type === 'password' ? 'text' : 'password';
}

// ── UX FIX: If the server returned an error, scroll the card into view ───────
window.addEventListener('DOMContentLoaded', () => {
    const errorBox = document.getElementById('error-msg');
    if (errorBox) {
        errorBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
});