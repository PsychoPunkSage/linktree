(function () {
  const canvas = document.getElementById('bg-canvas');
  const ctx = canvas.getContext('2d');

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  const N = 55;
  const nodes = Array.from({ length: N }, () => ({
    x: Math.random() * window.innerWidth,
    y: Math.random() * window.innerHeight,
    vx: (Math.random() - 0.5) * 0.35,
    vy: (Math.random() - 0.5) * 0.35,
    r: 1 + Math.random() * 3.5,
    pulse: Math.random() * Math.PI * 2,
    important: Math.random() > 0.82,
  }));

  const CONNECT_DIST = 130;

  function draw() {
    requestAnimationFrame(draw);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (let i = 0; i < N; i++) {
      for (let j = i + 1; j < N; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < CONNECT_DIST) {
          const t = 1 - dist / CONNECT_DIST;
          ctx.beginPath();
          ctx.moveTo(nodes[i].x, nodes[i].y);
          ctx.lineTo(nodes[j].x, nodes[j].y);
          ctx.strokeStyle = `rgba(34,197,94,${0.55 * t})`;
          ctx.lineWidth = 0.9 + t * 1.2;
          ctx.stroke();
        }
      }
    }

    nodes.forEach(n => {
      n.pulse += 0.018;
      const pr = Math.max(0.5, n.r + (n.important ? Math.sin(n.pulse) * 1.5 : 0));
      const alpha = n.important ? 0.7 + Math.sin(n.pulse) * 0.2 : 0.45;

      if (n.important) {
        const glowR = Math.max(1, pr * 5);
        const grd = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, glowR);
        grd.addColorStop(0, 'rgba(34,197,94,0.15)');
        grd.addColorStop(1, 'rgba(34,197,94,0)');
        ctx.beginPath();
        ctx.arc(n.x, n.y, glowR, 0, Math.PI * 2);
        ctx.fillStyle = grd;
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(n.x, n.y, pr, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(34,197,94,${alpha})`;
      ctx.fill();

      n.x += n.vx;
      n.y += n.vy;
      if (n.x < -20) n.x = canvas.width + 20;
      if (n.x > canvas.width + 20) n.x = -20;
      if (n.y < -20) n.y = canvas.height + 20;
      if (n.y > canvas.height + 20) n.y = -20;
    });
  }
  draw();
})();