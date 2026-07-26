"use client";

import { useEffect, useRef } from "react";
import type { PresenceState } from "@/lib/presence-protocol";

type LivingObsidianStageProps = {
  state: PresenceState;
  signal: number;
};

type Palette = {
  primary: string;
  secondary: string;
  tertiary: string;
  primaryRgb: [number, number, number];
  secondaryRgb: [number, number, number];
};

type Particle = {
  x: number;
  y: number;
  depth: number;
  size: number;
  drift: number;
  phase: number;
};

const TAU = Math.PI * 2;

const PARTICLES: Particle[] = Array.from({ length: 190 }, (_, index) => ({
  x: hash(index * 5.31 + 0.8),
  y: hash(index * 2.17 + 3.4),
  depth: 0.22 + hash(index * 7.91 + 1.2) * 0.78,
  size: 0.35 + hash(index * 11.73 + 2.8) * 1.45,
  drift: 0.08 + hash(index * 13.11 + 4.6) * 0.24,
  phase: hash(index * 17.03 + 8.1) * TAU,
}));

const ROUTES = Array.from({ length: 7 }, (_, index) => ({
  angle: -Math.PI * 0.84 + index * (Math.PI * 1.68) / 6,
  bend: (hash(index * 19.3 + 2.1) - 0.5) * 0.68,
  phase: hash(index * 23.7 + 5.4) * TAU,
}));

function hash(value: number) {
  return Math.abs(Math.sin(value * 12.9898 + 78.233) * 43758.5453) % 1;
}

function rgba(rgb: [number, number, number], alpha: number) {
  return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;
}

function paletteFor(state: PresenceState): Palette {
  if (state === "PLANNING" || state === "UNDERSTANDING") {
    return {
      primary: "#9f83ff",
      secondary: "#5de9ff",
      tertiary: "#dbcaff",
      primaryRgb: [159, 131, 255],
      secondaryRgb: [93, 233, 255],
    };
  }
  if (state === "WAITING_AUTHORITY" || state === "RECOVERING") {
    return {
      primary: "#ffc873",
      secondary: "#69d9f5",
      tertiary: "#fff0c7",
      primaryRgb: [255, 200, 115],
      secondaryRgb: [105, 217, 245],
    };
  }
  if (state === "BLOCKED" || state === "KILLED") {
    return {
      primary: "#ff6477",
      secondary: "#ffad6b",
      tertiary: "#ffd6dc",
      primaryRgb: [255, 100, 119],
      secondaryRgb: [255, 173, 107],
    };
  }
  if (state === "TELEMETRY_INCOMPLETE" || state === "DISCONNECTED") {
    return {
      primary: "#e87989",
      secondary: "#8c7fff",
      tertiary: "#f4c9d0",
      primaryRgb: [232, 121, 137],
      secondaryRgb: [140, 127, 255],
    };
  }
  if (state === "COMPLETED") {
    return {
      primary: "#dffeff",
      secondary: "#78f0cf",
      tertiary: "#ffffff",
      primaryRgb: [223, 254, 255],
      secondaryRgb: [120, 240, 207],
    };
  }
  return {
    primary: "#67e7ff",
    secondary: "#8e75ff",
    tertiary: "#d8fbff",
    primaryRgb: [103, 231, 255],
    secondaryRgb: [142, 117, 255],
  };
}

function stateSpeed(state: PresenceState) {
  if (state === "ACTING") return 1.7;
  if (state === "OBSERVING" || state === "VERIFYING") return 1.25;
  if (state === "PLANNING" || state === "UNDERSTANDING") return 1.08;
  if (state === "BLOCKED" || state === "TELEMETRY_INCOMPLETE") return 0.45;
  if (state === "SLEEPING") return 0.28;
  return 0.7;
}

export function LivingObsidianStage({ state, signal }: LivingObsidianStageProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pointerRef = useRef({ x: 0, y: 0, targetX: 0, targetY: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d", { alpha: true });
    if (!context) return;
    const stageCanvas = canvas;
    const stageContext = context;

    let frame = 0;
    let width = 0;
    let height = 0;
    let dpr = 1;
    let last = performance.now();
    let elapsed = 0;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const palette = paletteFor(state);
    const speed = stateSpeed(state);

    function resize() {
      const bounds = stageCanvas.getBoundingClientRect();
      width = Math.max(1, bounds.width);
      height = Math.max(1, bounds.height);
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      stageCanvas.width = Math.round(width * dpr);
      stageCanvas.height = Math.round(height * dpr);
      stageContext.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function onPointerMove(event: PointerEvent) {
      pointerRef.current.targetX = (event.clientX / window.innerWidth - 0.5) * 2;
      pointerRef.current.targetY = (event.clientY / window.innerHeight - 0.5) * 2;
    }

    function onPointerLeave() {
      pointerRef.current.targetX = 0;
      pointerRef.current.targetY = 0;
    }

    function render(now: number) {
      const delta = Math.min(32, now - last);
      last = now;
      if (!reducedMotion) elapsed += delta * 0.001 * speed;
      const t = elapsed + signal * 0.17;
      const pointer = pointerRef.current;
      pointer.x += (pointer.targetX - pointer.x) * 0.035;
      pointer.y += (pointer.targetY - pointer.y) * 0.035;

      stageContext.setTransform(dpr, 0, 0, dpr, 0, 0);
      stageContext.clearRect(0, 0, width, height);
      drawWorld(stageContext, width, height, t, pointer.x, pointer.y, palette, state);

      if (!reducedMotion) frame = window.requestAnimationFrame(render);
    }

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onPointerMove);
    document.documentElement.addEventListener("mouseleave", onPointerLeave);
    render(performance.now());

    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onPointerMove);
      document.documentElement.removeEventListener("mouseleave", onPointerLeave);
    };
  }, [signal, state]);

  return (
    <canvas
      aria-label={`Living Obsidian presence: ${state.replace(/_/g, " ").toLowerCase()}`}
      className="living-obsidian-canvas"
      ref={canvasRef}
      role="img"
    />
  );
}

function drawWorld(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  t: number,
  pointerX: number,
  pointerY: number,
  palette: Palette,
  state: PresenceState,
) {
  const compact = width < 720;
  const centerX = width * 0.5 + pointerX * (compact ? 4 : 11);
  const centerY = height * (compact ? 0.43 : 0.46) + pointerY * (compact ? 3 : 7);
  const radius = Math.max(70, Math.min(compact ? 132 : 205, Math.min(width, height) * (compact ? 0.22 : 0.24)));
  const pulse = 1 + Math.sin(t * 1.45) * (state === "SLEEPING" ? 0.008 : 0.018);
  const orbRadius = radius * pulse;

  drawAtmosphere(context, width, height, t, pointerX, pointerY, palette, state);
  drawParticles(context, width, height, t, pointerX, pointerY, palette, state);
  drawEnvironmentalState(context, centerX, centerY, orbRadius, width, height, t, palette, state);
  drawHalo(context, centerX, centerY, orbRadius, t, palette, state);
  drawOrb(context, centerX, centerY, orbRadius, t, palette, state);
  drawForegroundMist(context, width, height, centerX, centerY, orbRadius, t, palette);
}

function drawAtmosphere(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  t: number,
  pointerX: number,
  pointerY: number,
  palette: Palette,
  state: PresenceState,
) {
  const base = context.createLinearGradient(0, 0, width, height);
  base.addColorStop(0, "#010307");
  base.addColorStop(0.42, "#071019");
  base.addColorStop(0.68, "#050810");
  base.addColorStop(1, "#010205");
  context.fillStyle = base;
  context.fillRect(0, 0, width, height);

  const mood = state === "BLOCKED" || state === "TELEMETRY_INCOMPLETE" ? 1.18 : state === "COMPLETED" ? 1.3 : 1;
  const clouds = [
    { x: 0.15, y: 0.32, size: 0.48, color: palette.secondaryRgb, alpha: 0.12 },
    { x: 0.85, y: 0.45, size: 0.52, color: palette.primaryRgb, alpha: 0.14 },
    { x: 0.48, y: 0.56, size: 0.44, color: palette.primaryRgb, alpha: 0.1 },
    { x: 0.58, y: 0.16, size: 0.38, color: palette.secondaryRgb, alpha: 0.07 },
  ];

  for (let index = 0; index < clouds.length; index += 1) {
    const cloud = clouds[index];
    const driftX = Math.sin(t * (0.08 + index * 0.012) + index) * width * 0.035;
    const driftY = Math.cos(t * (0.065 + index * 0.01) + index * 1.7) * height * 0.045;
    const x = width * cloud.x + driftX + pointerX * width * 0.012 * (index % 2 ? -1 : 1);
    const y = height * cloud.y + driftY + pointerY * height * 0.008;
    const size = Math.max(width, height) * cloud.size;
    const gradient = context.createRadialGradient(x, y, 0, x, y, size);
    gradient.addColorStop(0, rgba(cloud.color, cloud.alpha * mood));
    gradient.addColorStop(0.28, rgba(cloud.color, cloud.alpha * 0.58 * mood));
    gradient.addColorStop(0.68, rgba(cloud.color, cloud.alpha * 0.13 * mood));
    gradient.addColorStop(1, rgba(cloud.color, 0));
    context.fillStyle = gradient;
    context.fillRect(0, 0, width, height);
  }

  context.save();
  context.globalCompositeOperation = "screen";
  context.lineCap = "round";
  for (let band = 0; band < 7; band += 1) {
    const y = height * (0.24 + band * 0.072);
    const amplitude = height * (0.045 + band * 0.004);
    context.beginPath();
    context.moveTo(-width * 0.08, y);
    for (let step = 0; step <= 32; step += 1) {
      const progress = step / 32;
      const x = progress * width * 1.16 - width * 0.08;
      const wave =
        Math.sin(progress * Math.PI * (2.2 + band * 0.09) + t * (0.12 + band * 0.018) + band) *
        amplitude;
      const pull = Math.sin(progress * Math.PI) * height * 0.035;
      context.lineTo(x, y + wave - pull);
    }
    context.strokeStyle = rgba(band % 2 ? palette.primaryRgb : palette.secondaryRgb, 0.018 + band * 0.004);
    context.lineWidth = 8 + band * 2.5;
    context.shadowBlur = 24;
    context.shadowColor = rgba(palette.primaryRgb, 0.18);
    context.stroke();
  }
  context.restore();
}

function drawParticles(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  t: number,
  pointerX: number,
  pointerY: number,
  palette: Palette,
  state: PresenceState,
) {
  const activity = state === "ACTING" ? 2.2 : state === "PLANNING" ? 1.4 : state === "SLEEPING" ? 0.45 : 1;
  context.save();
  context.globalCompositeOperation = "screen";
  for (const particle of PARTICLES) {
    const travel = t * particle.drift * 0.012 * activity;
    const x =
      ((particle.x + travel) % 1) * width +
      pointerX * particle.depth * 10 +
      Math.sin(t * 0.22 + particle.phase) * particle.depth * 5;
    const y =
      particle.y * height +
      pointerY * particle.depth * 7 +
      Math.cos(t * 0.18 + particle.phase) * particle.depth * 4;
    const flicker = 0.46 + Math.sin(t * 0.8 + particle.phase) * 0.28;
    context.beginPath();
    context.arc(x, y, particle.size * particle.depth, 0, TAU);
    context.fillStyle = rgba(
      particle.phase > Math.PI ? palette.primaryRgb : palette.secondaryRgb,
      (0.08 + particle.depth * 0.28) * flicker,
    );
    context.fill();
  }
  context.restore();
}

function drawEnvironmentalState(
  context: CanvasRenderingContext2D,
  centerX: number,
  centerY: number,
  radius: number,
  width: number,
  height: number,
  t: number,
  palette: Palette,
  state: PresenceState,
) {
  if (state === "PLANNING" || state === "UNDERSTANDING") {
    drawPlanningRoutes(context, centerX, centerY, radius, width, height, t, palette);
  } else if (state === "ACTING" || state === "OBSERVING" || state === "VERIFYING") {
    drawActionField(context, centerX, centerY, radius, width, t, palette, state);
  } else if (state === "LISTENING") {
    drawListeningField(context, centerX, centerY, radius, width, height, t, palette);
  } else if (state === "WAITING_AUTHORITY" || state === "RECOVERING") {
    drawAuthorityField(context, centerX, centerY, radius, t, palette, state);
  } else if (state === "BLOCKED" || state === "KILLED" || state === "TELEMETRY_INCOMPLETE") {
    drawFractureField(context, centerX, centerY, radius, width, height, t, palette, state);
  } else if (state === "COMPLETED") {
    drawProofConstellation(context, centerX, centerY, radius, t, palette);
  }
}

function drawPlanningRoutes(
  context: CanvasRenderingContext2D,
  centerX: number,
  centerY: number,
  radius: number,
  width: number,
  height: number,
  t: number,
  palette: Palette,
) {
  context.save();
  context.globalCompositeOperation = "screen";
  context.lineCap = "round";

  for (let index = 0; index < ROUTES.length; index += 1) {
    const route = ROUTES[index];
    const side = index < 4 ? -1 : 1;
    const originX = centerX + side * (radius * 1.35 + width * (0.16 + hash(index) * 0.09));
    const originY = centerY + Math.sin(route.angle) * height * 0.29;
    const endAngle = route.angle * 0.18;
    const endX = centerX + Math.cos(endAngle) * radius * 0.78;
    const endY = centerY + Math.sin(endAngle) * radius * 0.62;
    const accepted = index === 4;
    const reveal = Math.min(1, Math.max(0.12, (Math.sin(t * 0.58 + route.phase) + 1.35) * 0.54));

    context.beginPath();
    context.moveTo(originX, originY);
    context.bezierCurveTo(
      originX - side * width * (0.09 + route.bend * 0.03),
      originY + route.bend * height * 0.24,
      centerX + side * radius * 1.7,
      centerY - route.bend * radius,
      endX,
      endY,
    );
    context.setLineDash(accepted ? [] : [3, 11]);
    context.lineDashOffset = -t * (accepted ? 0 : 9);
    context.strokeStyle = rgba(
      accepted ? palette.secondaryRgb : palette.primaryRgb,
      accepted ? 0.88 : 0.36 + reveal * 0.3,
    );
    context.lineWidth = accepted ? 1.9 : 1.2;
    context.shadowBlur = accepted ? 18 : 8;
    context.shadowColor = rgba(accepted ? palette.secondaryRgb : palette.primaryRgb, accepted ? 0.8 : 0.28);
    context.stroke();

    const routeProgress = (t * 0.16 + index * 0.13) % 1;
    const markerX = originX + (endX - originX) * routeProgress;
    const markerY =
      originY +
      (endY - originY) * routeProgress +
      Math.sin(routeProgress * Math.PI) * route.bend * radius * 0.8;
    context.beginPath();
    context.arc(markerX, markerY, accepted ? 2.5 : 1.4, 0, TAU);
    context.fillStyle = accepted ? palette.secondary : rgba(palette.primaryRgb, 0.55);
    context.fill();

    context.beginPath();
    context.arc(originX, originY, accepted ? 5 : 3.2, 0, TAU);
    context.strokeStyle = rgba(accepted ? palette.secondaryRgb : palette.primaryRgb, accepted ? 0.72 : 0.36);
    context.lineWidth = 0.8;
    context.stroke();
  }

  context.translate(centerX, centerY);
  context.rotate(t * 0.035);
  for (let layer = 0; layer < 3; layer += 1) {
    const layerRadius = radius * (1.08 + layer * 0.12);
    context.beginPath();
    context.ellipse(
      0,
      0,
      layerRadius,
      layerRadius * (0.68 + layer * 0.04),
      layer * 0.7,
      -Math.PI * 0.82 + layer * 0.18,
      Math.PI * 0.42 + layer * 0.14,
    );
    context.strokeStyle = rgba(layer % 2 ? palette.secondaryRgb : palette.primaryRgb, 0.2 - layer * 0.035);
    context.lineWidth = 0.8;
    context.shadowBlur = 12;
    context.stroke();
  }
  context.setLineDash([]);
  context.restore();
}

function drawActionField(
  context: CanvasRenderingContext2D,
  centerX: number,
  centerY: number,
  radius: number,
  width: number,
  t: number,
  palette: Palette,
  state: PresenceState,
) {
  const direction = state === "OBSERVING" ? -1 : 1;
  const beamStart = direction > 0 ? centerX + radius * 0.72 : centerX - radius * 0.72;
  const beamEnd = direction > 0 ? width * 1.05 : -width * 0.05;
  const progress = (t * 0.42) % 1;

  context.save();
  context.globalCompositeOperation = "screen";
  const beam = context.createLinearGradient(beamStart, centerY, beamEnd, centerY);
  beam.addColorStop(0, rgba(palette.primaryRgb, 0.72));
  beam.addColorStop(0.34, rgba(palette.primaryRgb, 0.26));
  beam.addColorStop(1, rgba(palette.primaryRgb, 0));
  context.strokeStyle = beam;
  context.lineWidth = state === "ACTING" ? 2 : 1;
  context.shadowBlur = 28;
  context.shadowColor = palette.primary;
  context.beginPath();
  context.moveTo(beamStart, centerY);
  context.bezierCurveTo(
    centerX + direction * radius * 1.6,
    centerY - radius * 0.25,
    centerX + direction * radius * 2.3,
    centerY + radius * 0.2,
    beamEnd,
    centerY - radius * 0.08,
  );
  context.stroke();

  for (let index = 0; index < 9; index += 1) {
    const local = (progress + index / 9) % 1;
    const x = beamStart + (beamEnd - beamStart) * local;
    const y = centerY + Math.sin(local * Math.PI * 4 + index) * radius * 0.07;
    context.beginPath();
    context.arc(x, y, 1 + (1 - local) * 2.2, 0, TAU);
    context.fillStyle = rgba(index % 2 ? palette.primaryRgb : palette.secondaryRgb, 0.72 * (1 - local));
    context.fill();
  }

  if (state === "VERIFYING") {
    context.strokeStyle = rgba(palette.secondaryRgb, 0.32);
    context.lineWidth = 1;
    context.setLineDash([2, 8]);
    context.lineDashOffset = -t * 9;
    context.beginPath();
    context.arc(centerX, centerY, radius * 1.72, -Math.PI * 0.72, Math.PI * 0.72);
    context.stroke();
  }
  context.restore();
}

function drawListeningField(
  context: CanvasRenderingContext2D,
  centerX: number,
  centerY: number,
  radius: number,
  width: number,
  height: number,
  t: number,
  palette: Palette,
) {
  context.save();
  context.globalCompositeOperation = "screen";
  for (let index = 0; index < 5; index += 1) {
    const progress = (t * 0.14 + index / 5) % 1;
    const ringRadius = radius * (3.5 - progress * 2.4);
    context.beginPath();
    context.ellipse(centerX, centerY, ringRadius * 1.45, ringRadius, 0, 0, TAU);
    context.strokeStyle = rgba(palette.primaryRgb, 0.04 + progress * 0.18);
    context.lineWidth = 0.7 + progress;
    context.stroke();
  }

  const intake = context.createRadialGradient(centerX, centerY, radius, centerX, centerY, Math.max(width, height) * 0.55);
  intake.addColorStop(0, rgba(palette.primaryRgb, 0));
  intake.addColorStop(0.45, rgba(palette.primaryRgb, 0.04));
  intake.addColorStop(1, rgba(palette.primaryRgb, 0));
  context.fillStyle = intake;
  context.fillRect(0, 0, width, height);
  context.restore();
}

function drawAuthorityField(
  context: CanvasRenderingContext2D,
  centerX: number,
  centerY: number,
  radius: number,
  t: number,
  palette: Palette,
  state: PresenceState,
) {
  context.save();
  context.globalCompositeOperation = "screen";
  const ringRadius = radius * 1.48;
  context.translate(centerX, centerY);
  context.rotate(state === "RECOVERING" ? -t * 0.12 : Math.sin(t * 0.15) * 0.04);
  context.setLineDash(state === "RECOVERING" ? [7, 13] : [1, 8]);
  context.lineDashOffset = state === "RECOVERING" ? t * 9 : 0;
  context.strokeStyle = rgba(palette.primaryRgb, 0.44);
  context.lineWidth = 1.2;
  context.shadowBlur = 16;
  context.shadowColor = palette.primary;
  context.beginPath();
  context.arc(0, 0, ringRadius, -Math.PI * 0.9, Math.PI * 0.1);
  context.stroke();
  context.beginPath();
  context.arc(0, 0, ringRadius, Math.PI * 0.18, Math.PI * 0.82);
  context.stroke();

  for (let index = 0; index < 8; index += 1) {
    const angle = index * TAU / 8 + Math.PI / 8;
    const x = Math.cos(angle) * ringRadius;
    const y = Math.sin(angle) * ringRadius;
    context.fillStyle = index < 5 ? rgba(palette.primaryRgb, 0.68) : rgba(palette.primaryRgb, 0.14);
    context.fillRect(x - 1.5, y - 1.5, 3, 3);
  }
  context.restore();
}

function drawFractureField(
  context: CanvasRenderingContext2D,
  centerX: number,
  centerY: number,
  radius: number,
  width: number,
  height: number,
  t: number,
  palette: Palette,
  state: PresenceState,
) {
  const originX = centerX + radius * 0.2;
  const originY = centerY - radius * 0.1;
  const reach = state === "TELEMETRY_INCOMPLETE" ? 1.15 : 2.8;
  context.save();
  context.globalCompositeOperation = "screen";
  context.lineCap = "round";

  for (let branch = 0; branch < 6; branch += 1) {
    const angle = -Math.PI * 0.72 + branch * Math.PI * 0.25;
    context.beginPath();
    context.moveTo(originX, originY);
    let x = originX;
    let y = originY;
    const segments = 7;
    for (let segment = 1; segment <= segments; segment += 1) {
      const length = radius * reach / segments * (1 + branch * 0.09);
      x += Math.cos(angle + (hash(branch * 31 + segment) - 0.5) * 0.52) * length;
      y += Math.sin(angle + (hash(branch * 17 + segment) - 0.5) * 0.52) * length;
      context.lineTo(x, y);
    }
    const flicker = 0.68 + Math.sin(t * 3.2 + branch) * 0.16;
    context.strokeStyle = rgba(palette.primaryRgb, (0.16 + (6 - branch) * 0.035) * flicker);
    context.lineWidth = branch === 2 ? 2.1 : 0.9;
    context.shadowBlur = 18;
    context.shadowColor = palette.primary;
    context.stroke();
  }

  context.setLineDash([3, 13]);
  context.lineDashOffset = t * 7;
  context.strokeStyle = rgba(palette.secondaryRgb, state === "TELEMETRY_INCOMPLETE" ? 0.1 : 0.22);
  context.lineWidth = 0.8;
  context.beginPath();
  context.arc(originX, originY, radius * 1.52, -Math.PI * 0.92, Math.PI * 0.28);
  context.stroke();
  context.setLineDash([]);

  if (state === "TELEMETRY_INCOMPLETE") {
    context.fillStyle = rgba(palette.primaryRgb, 0.035 + Math.sin(t * 5) * 0.012);
    for (let line = 0; line < 4; line += 1) {
      const y = ((t * 24 + line * height * 0.27) % height);
      context.fillRect(0, y, width, 1);
    }
  }
  context.restore();
}

function drawProofConstellation(
  context: CanvasRenderingContext2D,
  centerX: number,
  centerY: number,
  radius: number,
  t: number,
  palette: Palette,
) {
  context.save();
  context.translate(centerX, centerY);
  context.rotate(t * 0.035);
  context.globalCompositeOperation = "screen";

  const points = Array.from({ length: 12 }, (_, index) => {
    const angle = index * TAU / 12;
    const wobble = 1 + Math.sin(t * 0.22 + index) * 0.015;
    return {
      x: Math.cos(angle) * radius * 1.72 * wobble,
      y: Math.sin(angle) * radius * 1.42 * wobble,
    };
  });

  context.strokeStyle = rgba(palette.secondaryRgb, 0.18);
  context.lineWidth = 0.7;
  context.beginPath();
  points.forEach((point, index) => {
    if (index === 0) context.moveTo(point.x, point.y);
    else context.lineTo(point.x, point.y);
  });
  context.closePath();
  context.stroke();

  for (let index = 0; index < points.length; index += 1) {
    const point = points[index];
    const settle = 0.64 + Math.sin(t * 0.52 + index) * 0.15;
    context.save();
    context.translate(point.x, point.y);
    context.rotate(Math.PI / 4);
    context.fillStyle = rgba(index % 3 ? palette.primaryRgb : palette.secondaryRgb, settle);
    context.shadowBlur = 14;
    context.shadowColor = index % 3 ? palette.primary : palette.secondary;
    context.fillRect(-2.2, -2.2, 4.4, 4.4);
    context.restore();
  }
  context.restore();
}

function drawHalo(
  context: CanvasRenderingContext2D,
  centerX: number,
  centerY: number,
  radius: number,
  t: number,
  palette: Palette,
  state: PresenceState,
) {
  const intensity = state === "COMPLETED" ? 1.55 : state === "SLEEPING" ? 0.56 : 1;
  const glow = context.createRadialGradient(centerX, centerY, radius * 0.48, centerX, centerY, radius * 2.45);
  glow.addColorStop(0, rgba(palette.primaryRgb, 0.18 * intensity));
  glow.addColorStop(0.36, rgba(palette.primaryRgb, 0.09 * intensity));
  glow.addColorStop(0.68, rgba(palette.secondaryRgb, 0.035 * intensity));
  glow.addColorStop(1, rgba(palette.primaryRgb, 0));
  context.fillStyle = glow;
  context.fillRect(centerX - radius * 2.6, centerY - radius * 2.6, radius * 5.2, radius * 5.2);

  context.save();
  context.translate(centerX, centerY);
  context.rotate(t * 0.055);
  context.globalCompositeOperation = "screen";
  context.lineWidth = 0.8;
  for (let ring = 0; ring < 3; ring += 1) {
    const ringRadius = radius * (1.08 + ring * 0.22);
    context.setLineDash([1 + ring, 12 + ring * 5]);
    context.lineDashOffset = -t * (4 + ring * 1.8);
    context.strokeStyle = rgba(ring % 2 ? palette.secondaryRgb : palette.primaryRgb, 0.11 + ring * 0.025);
    context.beginPath();
    context.ellipse(0, 0, ringRadius, ringRadius * (0.72 + ring * 0.05), ring * 0.7, 0, TAU);
    context.stroke();
  }
  context.restore();
}

function drawOrb(
  context: CanvasRenderingContext2D,
  centerX: number,
  centerY: number,
  radius: number,
  t: number,
  palette: Palette,
  state: PresenceState,
) {
  context.save();
  context.translate(centerX, centerY);

  context.save();
  context.beginPath();
  context.arc(0, 0, radius, 0, TAU);
  context.clip();

  const body = context.createRadialGradient(-radius * 0.32, -radius * 0.38, radius * 0.04, 0, 0, radius * 1.12);
  body.addColorStop(0, "#1a2935");
  body.addColorStop(0.2, "#101923");
  body.addColorStop(0.55, "#05080e");
  body.addColorStop(0.84, "#010206");
  body.addColorStop(1, "#000104");
  context.fillStyle = body;
  context.fillRect(-radius, -radius, radius * 2, radius * 2);

  const internalGlow = context.createRadialGradient(
    -radius * 0.1,
    radius * 0.05,
    0,
    -radius * 0.1,
    radius * 0.05,
    radius * 0.82,
  );
  internalGlow.addColorStop(0, rgba(palette.primaryRgb, state === "SLEEPING" ? 0.11 : 0.25));
  internalGlow.addColorStop(0.35, rgba(palette.secondaryRgb, 0.08));
  internalGlow.addColorStop(1, rgba(palette.primaryRgb, 0));
  context.fillStyle = internalGlow;
  context.fillRect(-radius, -radius, radius * 2, radius * 2);

  context.globalCompositeOperation = "screen";
  context.lineCap = "round";
  for (let band = 0; band < 18; band += 1) {
    const y = -radius * 0.78 + band * radius * 0.092;
    const phase = t * (0.12 + band * 0.003) + band * 0.71;
    const alpha = 0.025 + hash(band * 2.8) * 0.085;
    context.beginPath();
    context.moveTo(-radius * 1.15, y);
    context.bezierCurveTo(
      -radius * 0.48,
      y + Math.sin(phase) * radius * 0.3,
      radius * 0.2,
      y - Math.cos(phase * 0.88) * radius * 0.34,
      radius * 1.15,
      y + Math.sin(phase * 0.7) * radius * 0.12,
    );
    context.strokeStyle = rgba(band % 3 ? palette.primaryRgb : palette.secondaryRgb, alpha);
    context.lineWidth = 0.45 + hash(band * 4.7) * 1.5;
    context.shadowBlur = 5;
    context.shadowColor = palette.primary;
    context.stroke();
  }

  drawObsidianFacets(context, radius, t, palette, state);
  drawVeins(context, radius, t, palette, state);

  const shade = context.createLinearGradient(-radius, -radius, radius, radius);
  shade.addColorStop(0, "rgba(255,255,255,0.12)");
  shade.addColorStop(0.16, "rgba(255,255,255,0.01)");
  shade.addColorStop(0.58, "rgba(0,0,0,0.1)");
  shade.addColorStop(1, "rgba(0,0,0,0.86)");
  context.globalCompositeOperation = "source-over";
  context.fillStyle = shade;
  context.fillRect(-radius, -radius, radius * 2, radius * 2);
  context.restore();

  context.globalCompositeOperation = "screen";
  context.strokeStyle = rgba(palette.primaryRgb, state === "SLEEPING" ? 0.2 : 0.48);
  context.lineWidth = 1.1;
  context.shadowBlur = 20;
  context.shadowColor = palette.primary;
  context.beginPath();
  context.arc(0, 0, radius, -Math.PI * 0.8, Math.PI * 0.36);
  context.stroke();

  context.strokeStyle = "rgba(255,255,255,0.14)";
  context.lineWidth = 0.55;
  context.shadowBlur = 0;
  context.beginPath();
  context.arc(0, 0, radius - 1, Math.PI * 1.12, Math.PI * 1.72);
  context.stroke();

  const vortexWidth = radius * (state === "LISTENING" ? 0.31 : state === "SLEEPING" ? 0.16 : 0.24);
  const vortexHeight = radius * (state === "LISTENING" ? 0.055 : state === "BLOCKED" ? 0.025 : 0.04);
  const vortex = context.createRadialGradient(0, radius * 0.04, 0, 0, radius * 0.04, vortexWidth);
  vortex.addColorStop(0, palette.tertiary);
  vortex.addColorStop(0.16, rgba(palette.primaryRgb, 0.92));
  vortex.addColorStop(0.46, rgba(palette.secondaryRgb, 0.34));
  vortex.addColorStop(1, rgba(palette.primaryRgb, 0));
  context.fillStyle = vortex;
  context.shadowBlur = state === "SLEEPING" ? 14 : 34;
  context.shadowColor = palette.primary;
  context.beginPath();
  context.ellipse(0, radius * 0.04, vortexWidth, vortexHeight, -0.08, 0, TAU);
  context.fill();

  for (let ring = 0; ring < 4; ring += 1) {
    context.save();
    context.rotate(-0.22 + ring * 0.16 + Math.sin(t * 0.08 + ring) * 0.025);
    context.strokeStyle = rgba(ring % 2 ? palette.secondaryRgb : palette.primaryRgb, 0.2 - ring * 0.03);
    context.lineWidth = 0.6;
    context.beginPath();
    context.ellipse(0, radius * 0.04, vortexWidth * (1.35 + ring * 0.28), radius * (0.09 + ring * 0.035), 0, 0, TAU);
    context.stroke();
    context.restore();
  }

  context.restore();
}

function drawObsidianFacets(
  context: CanvasRenderingContext2D,
  radius: number,
  t: number,
  palette: Palette,
  state: PresenceState,
) {
  const strength = state === "SLEEPING" ? 0.42 : state === "COMPLETED" ? 1.15 : 0.82;
  const nodes = Array.from({ length: 28 }, (_, index) => {
    const angle = hash(index * 7.31 + 4.2) * TAU;
    const distance = radius * (0.22 + Math.sqrt(hash(index * 4.17 + 8.6)) * 0.7);
    return {
      x: Math.cos(angle) * distance,
      y: Math.sin(angle) * distance,
    };
  });

  context.save();
  context.globalCompositeOperation = "screen";
  for (let index = 0; index < nodes.length; index += 1) {
    const from = nodes[index];
    const to = nodes[(index * 7 + 5) % nodes.length];
    const distance = Math.hypot(from.x - to.x, from.y - to.y);
    if (distance > radius * 0.88) continue;
    context.beginPath();
    context.moveTo(from.x, from.y);
    context.lineTo(to.x, to.y);
    context.strokeStyle = rgba(
      index % 4 ? palette.primaryRgb : palette.secondaryRgb,
      (0.025 + hash(index * 9.4) * 0.045) * strength,
    );
    context.lineWidth = 0.45;
    context.stroke();
  }

  for (let patch = 0; patch < 6; patch += 1) {
    const angle = patch * TAU / 6 + t * 0.006;
    const x = Math.cos(angle) * radius * 0.38;
    const y = Math.sin(angle) * radius * 0.31;
    const glow = context.createRadialGradient(x, y, 0, x, y, radius * 0.34);
    glow.addColorStop(0, rgba(patch % 2 ? palette.primaryRgb : palette.secondaryRgb, 0.045 * strength));
    glow.addColorStop(1, rgba(palette.primaryRgb, 0));
    context.fillStyle = glow;
    context.fillRect(-radius, -radius, radius * 2, radius * 2);
  }
  context.restore();
}

function drawVeins(
  context: CanvasRenderingContext2D,
  radius: number,
  t: number,
  palette: Palette,
  state: PresenceState,
) {
  const active = state === "SLEEPING" ? 0.36 : state === "COMPLETED" ? 1.35 : 1;
  context.save();
  context.globalCompositeOperation = "screen";
  context.lineCap = "round";

  for (let vein = 0; vein < 11; vein += 1) {
    const originAngle = hash(vein * 4.11 + 1.3) * TAU;
    const startRadius = radius * (0.08 + hash(vein * 7.2) * 0.22);
    let x = Math.cos(originAngle) * startRadius;
    let y = Math.sin(originAngle) * startRadius;
    context.beginPath();
    context.moveTo(x, y);
    for (let segment = 1; segment <= 8; segment += 1) {
      const progress = segment / 8;
      const angle =
        originAngle +
        (hash(vein * 31 + segment * 7.7) - 0.5) * 0.44 +
        Math.sin(t * 0.08 + vein) * 0.025;
      const length = radius * (0.07 + hash(vein * 11 + segment) * 0.055);
      x += Math.cos(angle) * length;
      y += Math.sin(angle) * length;
      if (Math.hypot(x, y) > radius * 0.92) break;
      context.lineTo(x, y);
    }
    const bright = vein === 3 || vein === 8;
    context.strokeStyle = rgba(
      bright ? palette.primaryRgb : palette.secondaryRgb,
      (bright ? 0.52 : 0.16) * active,
    );
    context.lineWidth = bright ? 1.25 : 0.52;
    context.shadowBlur = bright ? 12 : 5;
    context.shadowColor = bright ? palette.primary : palette.secondary;
    context.stroke();
  }
  context.restore();
}

function drawForegroundMist(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  centerX: number,
  centerY: number,
  radius: number,
  t: number,
  palette: Palette,
) {
  context.save();
  context.globalCompositeOperation = "screen";
  const floor = context.createRadialGradient(
    centerX,
    centerY + radius * 1.08,
    0,
    centerX,
    centerY + radius * 1.08,
    radius * 1.85,
  );
  floor.addColorStop(0, rgba(palette.primaryRgb, 0.13 + Math.sin(t * 0.6) * 0.018));
  floor.addColorStop(0.35, rgba(palette.secondaryRgb, 0.035));
  floor.addColorStop(1, rgba(palette.primaryRgb, 0));
  context.scale(1, 0.34);
  context.fillStyle = floor;
  context.fillRect(0, (centerY + radius * 0.2) / 0.34, width, height);
  context.restore();
}
