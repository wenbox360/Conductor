// File: mcphardware/src/components/Scene3D.tsx
'use client';

import { Cpu, Zap, Radio, Wifi } from 'lucide-react';

export default function Scene3D(){
  return (
    <div className="card w-full h-[300px] md:h-[400px] rounded-xl flex items-center justify-center bg-surface-subtle">
      <div className="text-center space-y-6">
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="flex flex-col items-center space-y-2 p-4 rounded-lg bg-surface">
            <Cpu className="w-8 h-8 text-accent" />
            <span className="text-sm text-muted font-medium">Processors</span>
          </div>
          <div className="flex flex-col items-center space-y-2 p-4 rounded-lg bg-surface">
            <Zap className="w-8 h-8 text-accent-warm" />
            <span className="text-sm text-muted font-medium">Power</span>
          </div>
          <div className="flex flex-col items-center space-y-2 p-4 rounded-lg bg-surface">
            <Radio className="w-8 h-8 text-accent-emerald" />
            <span className="text-sm text-muted font-medium">Sensors</span>
          </div>
          <div className="flex flex-col items-center space-y-2 p-4 rounded-lg bg-surface">
            <Wifi className="w-8 h-8 text-accent-purple" />
            <span className="text-sm text-muted font-medium">Connectivity</span>
          </div>
        </div>
        <div className="text-center">
          <h3 className="text-lg font-medium text-ink mb-2">Hardware Overview</h3>
          <p className="text-sm text-muted max-w-xs">
            Connect and control various hardware components through a unified interface
          </p>
        </div>
      </div>
    </div>
  );
}
