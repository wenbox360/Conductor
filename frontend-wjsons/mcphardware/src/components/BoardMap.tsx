// mcphardware/src/components/BoardMap.tsx
'use client';

import React, { useEffect, useMemo, useState } from 'react';
import type { BoardDef } from '@/lib/boards';

type Props = {
  board: BoardDef;
  selectedPins: number[];
  onToggle(pin: number): void;
  /** Pins that should be unselectable (e.g., 5V / 3V3 / GND or already-used) */
  disabledPins?: number[];
};

export default function BoardMap({
  board,
  selectedPins,
  onToggle,
  disabledPins,
}: Props) {
  // Mirror the photo’s aspect so the overlay always lands correctly.
  const [ratio, setRatio] = useState(768 / 1177); // good fallback for the Pi 5 photo
  useEffect(() => {
    const img = new Image();
    img.src = board.image;
    img.onload = () => {
      if (img.naturalWidth && img.naturalHeight) {
        setRatio(img.naturalHeight / img.naturalWidth);
      }
    };
  }, [board.image]);

  // SVG logical space
  const W = 1000;
  const H = Math.round(W * ratio);

  // Where the 2×N header is on the photo (board.header is in 0..1)
  const header = useMemo(
    () => ({
      x: board.header.x * W,
      y: board.header.y * H,
      w: board.header.w * W,
      h: board.header.h * H,
    }),
    [board.header, W, H]
  );

  const rows = board.rows; // 20 on Pi
  const horizontal = header.w >= header.h; // auto-detect orientation

  // Disabled set (fast lookups)
  const disabled = useMemo(() => new Set(disabledPins ?? []), [disabledPins]);

  // Compute pin centers
  const pins = useMemo(() => {
    const out: { num: number; x: number; y: number }[] = [];
    
    // Check for custom layout
    if (board.customLayout) {
      const { pinGroups } = board.customLayout;
      
      for (const group of pinGroups) {
        const pinCount = group.endPin - group.startPin + 1;
        const startX = group.x * W;
        const y = group.y * H;
        const width = group.width * W;
        
        for (let i = 0; i < pinCount; i++) {
          const pinNum = group.startPin + i;
          const x = startX + (i / (pinCount - 1)) * width;
          out.push({ num: pinNum, x, y });
        }
      }
    } else if (horizontal) {
      // Horizontal 2×N along X (Pi-5 photo)
      const topY = header.y + header.h * 0.35;
      const botY = header.y + header.h * 0.72;
      const start = header.x + header.w * 0.02;
      const gapX = header.w * (0.96 / (rows - 1));
      for (let i = 0; i < rows; i++) {
        const x = start + i * gapX;
        out.push({ num: 1 + i * 2, x, y: topY });
        out.push({ num: 2 + i * 2, x, y: botY });
      }
    } else {
      // Vertical 2×N along Y (fallback)
      const leftX = header.x + header.w * 0.28;
      const rightX = header.x + header.w * 0.72;
      const topY = header.y + header.h * 0.03;
      const gapY = header.h * (0.94 / (rows - 1));
      for (let i = 0; i < rows; i++) {
        const y = topY + i * gapY;
        out.push({ num: 1 + i * 2, x: leftX, y });
        out.push({ num: 2 + i * 2, x: rightX, y });
      }
    }
    return out;
  }, [board.customLayout, horizontal, header.x, header.y, header.w, header.h, rows, W, H]);

  // Visual helpers
  const rad = Math.max(9, Math.min(16, (horizontal ? header.h : header.w) * 0.065));
  const isSel = (n: number) => selectedPins.includes(n);
  const labelFor = (n: number) =>
    (n % 2 ? board.oddLabels?.[n] : board.evenLabels?.[n]) ?? '';
  const colorFor = (n: number) =>
    board.v5?.includes(n)
      ? '#FF5A5A'
      : board.v33?.includes(n)
      ? '#FFB857'
      : board.gnd?.includes(n)
      ? '#8A93A5'
      : '#1A1E27';

  const [hover, setHover] = useState<number | null>(null);

  return (
    <div className="relative rounded-2xl border border-white/10 bg-[rgba(255,255,255,0.03)]">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-auto block select-none"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Board photo */}
        <image href={board.image} x={0} y={0} width={W} height={H} />

        {/* Header guide (subtle) */}
        <rect
          x={header.x}
          y={header.y}
          width={header.w}
          height={header.h}
          rx={8}
          fill="none"
          stroke="rgba(255,255,255,.14)"
        />

        {/* Pins */}
        {pins.map((p) => {
          const isDisabled = disabled.has(p.num);
          return (
            <g
              key={p.num}
              transform={`translate(${p.x},${p.y})`}
              onClick={() => {
                if (!isDisabled) onToggle(p.num);
              }}
              onPointerEnter={() => {
                if (!isDisabled) setHover(p.num);
              }}
              onPointerLeave={() => setHover((h) => (h === p.num ? null : h))}
              style={{
                cursor: isDisabled ? 'not-allowed' : 'pointer',
                opacity: isDisabled ? 0.55 : 1,
              }}
            >
              <circle
                r={rad + 6}
                fill={
                  isSel(p.num)
                    ? 'rgba(86,235,210,.22)'
                    : hover === p.num && !isDisabled
                    ? 'rgba(255,255,255,.10)'
                    : 'transparent'
                }
              />
              <circle
                r={rad}
                fill={colorFor(p.num)}
                stroke={
                  isSel(p.num) ? 'hsl(190 95% 55%)' : 'rgba(255,255,255,.45)'
                }
                strokeWidth={isSel(p.num) ? 3 : 1.2}
              />
              {labelFor(p.num) && (
                <text
                  y={-rad - 8}
                  textAnchor="middle"
                  fontSize={10}
                  fill="#A6ADBB"
                >
                  {labelFor(p.num)}
                </text>
              )}
              <text
                y={rad + 14}
                textAnchor="middle"
                fontSize={11}
                fill="#E6E8EF"
              >
                {p.num}
              </text>
            </g>
          );
        })}

        {/* Tooltip */}
        {hover && (() => {
          const p = pins.find((x) => x.num === hover)!;
          const text = labelFor(hover)
            ? `${hover} · ${labelFor(hover)}`
            : String(hover);
          const tw = Math.max(72, text.length * 7.2); // rough width estimate
          return (
            <g transform={`translate(${p.x},${p.y - rad - 28})`}>
              <rect
                x={-tw / 2}
                y={-18}
                rx={8}
                width={tw}
                height={24}
                fill="rgba(0,0,0,.65)"
                stroke="rgba(255,255,255,.12)"
              />
              <text
                x={0}
                y={0}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={12}
                fill="#E6E8EF"
              >
                {text}
              </text>
            </g>
          );
        })()}
      </svg>
    </div>
  );
}
