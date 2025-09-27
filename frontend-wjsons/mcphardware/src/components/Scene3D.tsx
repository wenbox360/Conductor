// File: mcphardware/src/components/Scene3D.tsx
'use client';

import { Suspense, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { Environment, OrbitControls, ContactShadows, Float } from '@react-three/drei';
import * as THREE from 'three';

function ProceduralOrb(){
  const mat = useMemo(()=> new THREE.MeshPhysicalMaterial({
    color: new THREE.Color('#56EBD2'),
    roughness:.12, metalness:.65, clearcoat:.8, transmission:.22, thickness:.9,
  }), []);
  return (
    <Float floatIntensity={1.2} rotationIntensity={0.5} speed={1.2}>
      <mesh castShadow receiveShadow>
        <icosahedronGeometry args={[1.25, 2]} />
        <primitive object={mat} attach="material" />
      </mesh>
    </Float>
  );
}

export default function Scene3D(){
  return (
    <div className="shine card--gradient w-full h-[360px] md:h-[460px] rounded-2xl overflow-hidden border border-white/10">
      <Canvas camera={{ position:[0,1.4,4], fov:42 }} shadows>
        <Suspense fallback={null}>
          <ambientLight intensity={0.55} />
          <directionalLight position={[4,8,6]} intensity={1.1} castShadow />
          <ProceduralOrb />
          <ContactShadows opacity={0.35} scale={10} blur={2} far={3} />
          <Environment preset="city" />
          <OrbitControls enablePan={false} minDistance={3} maxDistance={7} />
        </Suspense>
      </Canvas>
    </div>
  );
}
