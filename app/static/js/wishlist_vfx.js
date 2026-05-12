// Wishlist Starfield VFX — canvas-based shooting stars
// Only active on the wishlist page

(function () {
  let canvas, ctx, animId;
  let stars = [];
  let shootingStars = [];
  const STAR_COUNT = 80;
  const SHOOTING_STAR_INTERVAL = 3000; // ms between shooting stars

  function rand(min, max) {
    return Math.random() * (max - min) + min;
  }

  function createStars(w, h) {
    stars = [];
    for (let i = 0; i < STAR_COUNT; i++) {
      stars.push({
        x: rand(0, w),
        y: rand(0, h),
        r: rand(0.5, 2),
        alpha: rand(0.3, 0.9),
        pulse: rand(0.005, 0.02),
        pulseDir: 1,
      });
    }
  }

  function createShootingStar(w, h) {
    const fromLeft = Math.random() > 0.5;
    return {
      x: fromLeft ? rand(0, w * 0.3) : rand(w * 0.3, w),
      y: rand(0, h * 0.4),
      vx: rand(3, 7),
      vy: rand(1.5, 4),
      len: rand(40, 100),
      alpha: rand(0.6, 1),
      life: 1,
      decay: rand(0.008, 0.02),
    };
  }

  function draw() {
    if (!canvas || !ctx) return;
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    // Background stars
    stars.forEach((s) => {
      s.alpha += s.pulse * s.pulseDir;
      if (s.alpha >= 0.9) s.pulseDir = -1;
      if (s.alpha <= 0.3) s.pulseDir = 1;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${s.alpha.toFixed(2)})`;
      ctx.fill();
    });

    // Shooting stars
    shootingStars.forEach((ss) => {
      const grad = ctx.createLinearGradient(
        ss.x, ss.y,
        ss.x - ss.vx * ss.len / 10, ss.y - ss.vy * ss.len / 10
      );
      grad.addColorStop(0, `rgba(255,255,255,${ss.alpha.toFixed(2)})`);
      grad.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.beginPath();
      ctx.moveTo(ss.x, ss.y);
      ctx.lineTo(
        ss.x - ss.vx * ss.len / 10,
        ss.y - ss.vy * ss.len / 10
      );
      ctx.strokeStyle = grad;
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ss.x += ss.vx;
      ss.y += ss.vy;
      ss.life -= ss.decay;
      ss.alpha = ss.life;
    });

    shootingStars = shootingStars.filter((ss) => ss.life > 0);

    animId = requestAnimationFrame(draw);
  }

  function resize() {
    if (!canvas) return;
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    createStars(canvas.width, canvas.height);
  }

  function spawnShootingStar() {
    if (!canvas) return;
    shootingStars.push(createShootingStar(canvas.width, canvas.height));
  }

  function init() {
    // Only on wishlist page
    if (document.body.dataset.page !== 'wishlist') return;

    canvas = document.createElement('canvas');
    canvas.id = 'starfieldCanvas';
    canvas.style.cssText =
      'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;';
    document.body.prepend(canvas);
    ctx = canvas.getContext('2d');

    resize();
    window.addEventListener('resize', resize);

    // Periodic shooting stars
    const intervalId = setInterval(spawnShootingStar, SHOOTING_STAR_INTERVAL);
    // Spawn one immediately
    setTimeout(spawnShootingStar, 1500);

    draw();

    // Store cleanup reference
    canvas._starfieldInterval = intervalId;
  }

  function destroy() {
    if (animId) cancelAnimationFrame(animId);
    if (canvas) {
      if (canvas._starfieldInterval) clearInterval(canvas._starfieldInterval);
      canvas.remove();
      canvas = null;
      ctx = null;
    }
    window.removeEventListener('resize', resize);
  }

  // Auto-init on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose for manual control
  window.StarfieldVFX = { init, destroy };
})();
