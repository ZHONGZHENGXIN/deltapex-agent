"use client";

import { useEffect, useRef } from "react";
import { useReducedMotion } from "framer-motion";

type ParticleRecord = {
  x: number;
  y: number;
  baseX: number;
  baseY: number;
  size: number;
  baseSize: number;
  density: number;
  angle: number;
  pulseSpeed: number;
};

const BASE_BACKGROUND = "#f6f3f1";
const PARTICLE_COLOR = "183, 28, 28";

export default function InteractiveHeroBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const shouldReduceMotion = useReducedMotion();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    let animationFrameId = 0;
    let particles: ParticleRecord[] = [];
    const mouse = { x: 0, y: 0, radius: 150 };

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      init();
    };

    const handleMouseMove = (event: MouseEvent) => {
      mouse.x = event.clientX;
      mouse.y = event.clientY;
    };

    const handleMouseLeave = () => {
      mouse.x = -9999;
      mouse.y = -9999;
    };

    const init = () => {
      particles = [];
      const numberOfParticles = (canvas.width * canvas.height) / 5000;

      for (let i = 0; i < numberOfParticles; i += 1) {
        const x = Math.random() * canvas.width;
        const y = Math.random() * canvas.height;
        particles.push({
          x,
          y,
          baseX: x,
          baseY: y,
          baseSize: Math.random() * 2 + 1,
          size: 0,
          density: Math.random() * 30 + 1,
          angle: Math.random() * Math.PI * 2,
          pulseSpeed: 0.02 + Math.random() * 0.03,
        });
      }
    };

    const drawParticle = (particle: ParticleRecord) => {
      const pulse = Math.sin(particle.angle) * 0.2 + 0.8;
      const opacity = 0.3 * pulse;
      const currentSize = particle.baseSize * (0.9 + pulse * 0.1);

      context.fillStyle = `rgba(${PARTICLE_COLOR}, ${opacity})`;
      context.beginPath();
      context.arc(particle.x, particle.y, currentSize, 0, Math.PI * 2);
      context.closePath();
      context.fill();
    };

    const updateParticle = (particle: ParticleRecord) => {
      particle.angle += particle.pulseSpeed;

      if (!shouldReduceMotion) {
        const dx = mouse.x - particle.x;
        const dy = mouse.y - particle.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance > 0 && distance < mouse.radius) {
          const forceDirectionX = dx / distance;
          const forceDirectionY = dy / distance;
          const force = (mouse.radius - distance) / mouse.radius;
          const directionX = forceDirectionX * force * particle.density;
          const directionY = forceDirectionY * force * particle.density;

          particle.x -= directionX;
          particle.y -= directionY;
        } else {
          if (particle.x !== particle.baseX) {
            particle.x -= (particle.x - particle.baseX) / 20;
          }
          if (particle.y !== particle.baseY) {
            particle.y -= (particle.y - particle.baseY) / 20;
          }
        }
      }
    };

    const connect = () => {
      for (let i = 0; i < particles.length; i += 1) {
        for (let j = i; j < particles.length; j += 1) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < 100) {
            const opacity = (1 - distance / 100) * 0.15;
            context.strokeStyle = `rgba(${PARTICLE_COLOR}, ${opacity})`;
            context.lineWidth = 1;
            context.beginPath();
            context.moveTo(particles[i].x, particles[i].y);
            context.lineTo(particles[j].x, particles[j].y);
            context.stroke();
          }
        }
      }
    };

    const render = () => {
      context.fillStyle = BASE_BACKGROUND;
      context.fillRect(0, 0, canvas.width, canvas.height);

      for (const particle of particles) {
        updateParticle(particle);
        drawParticle(particle);
      }

      connect();
      animationFrameId = window.requestAnimationFrame(render);
    };

    resize();

    if (!shouldReduceMotion) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseleave", handleMouseLeave);
    }

    window.addEventListener("resize", resize);
    render();

    return () => {
      window.cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, [shouldReduceMotion]);

  return <canvas ref={canvasRef} className="pointer-events-none fixed inset-0 z-0 h-full w-full" />;
}
