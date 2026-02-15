'use client';

import { useEffect, useRef } from 'react';

const ASCII_CHARS = ['·', '+', '*', ':', '∑', '|', '○', '△'];

function smoothstep(edge0, edge1, x) {
    const t = Math.max(0, Math.min(1, (x - edge0) / (edge1 - edge0)));
    return t * t * (3 - 2 * t);
}

function safeBandAttenuation(x, y, width, height) {
    const safeCenterX = width * 0.38;
    const safeCenterY = height * 0.45;
    const rx = width * 0.36;
    const ry = height * 0.38;
    const nx = (x - safeCenterX) / rx;
    const ny = (y - safeCenterY) / ry;
    const d = Math.sqrt(nx * nx + ny * ny);
    const lift = smoothstep(0.62, 1.1, d);
    return 0.72 + (0.28 * lift);
}

export default function AsciiParticles() {
    const canvasRef = useRef(null);
    const particles = useRef([]);
    const animationFrame = useRef(null);
    const mouse = useRef({ x: -1000, y: -1000 });

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        let width = window.innerWidth;
        let height = window.innerHeight;

        const resize = () => {
            width = window.innerWidth;
            height = window.innerHeight;
            canvas.width = width;
            canvas.height = height;
        };

        resize();
        window.addEventListener('resize', resize);

        // Track mouse for interactive repelling
        const handleMouse = (e) => {
            mouse.current = { x: e.clientX, y: e.clientY };
        };
        window.addEventListener('mousemove', handleMouse);

        const PARTICLE_COUNT = Math.floor((width * height) / 5600);
        particles.current = Array.from({ length: PARTICLE_COUNT }, () => ({
            x: Math.random() * width,
            y: Math.random() * height,
            char: ASCII_CHARS[Math.floor(Math.random() * ASCII_CHARS.length)],
            baseOpacity: Math.random() * 0.18 + 0.14,
            speed: Math.random() * 0.12 + 0.04,
            drift: (Math.random() - 0.5) * 0.11,
            size: Math.random() * 3.4 + 9.8,
            phase: Math.random() * Math.PI * 2,
            pulseSpeed: Math.random() * 0.006 + 0.003,
        }));

        const animate = () => {
            ctx.clearRect(0, 0, width, height);
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';

            for (const p of particles.current) {
                p.phase += p.pulseSpeed;
                const pulse = 0.5 + 0.5 * Math.sin(p.phase);
                let opacity = p.baseOpacity * (0.5 + 0.5 * pulse);

                // Move upward
                p.y -= p.speed;
                p.x += p.drift + Math.sin(p.phase * 0.5) * 0.1;

                // Mouse interaction — particles glow near cursor
                const dx = p.x - mouse.current.x;
                const dy = p.y - mouse.current.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 130) {
                    opacity = Math.min(opacity * 1.35, 0.42);
                }

                opacity *= safeBandAttenuation(p.x, p.y, width, height);

                // Wrap
                if (p.y < -20) {
                    p.y = height + 20;
                    p.x = Math.random() * width;
                }
                if (p.x < -20) p.x = width + 20;
                if (p.x > width + 20) p.x = -20;

                // Draw
                ctx.font = `${p.size}px "JetBrains Mono", monospace`;
                ctx.fillStyle = `rgba(232, 184, 75, ${opacity})`;
                ctx.fillText(p.char, p.x, p.y);
            }

            animationFrame.current = requestAnimationFrame(animate);
        };

        animate();

        return () => {
            window.removeEventListener('resize', resize);
            window.removeEventListener('mousemove', handleMouse);
            if (animationFrame.current) {
                cancelAnimationFrame(animationFrame.current);
            }
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            id="ascii-particles"
            style={{
                position: 'fixed',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                pointerEvents: 'none',
                zIndex: 0,
            }}
        />
    );
}
