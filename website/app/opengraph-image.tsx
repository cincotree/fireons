import { ImageResponse } from 'next/og';
import { readFileSync } from 'fs';
import { join } from 'path';

export const dynamic = 'force-static';
export const alt = 'Fireons — Community for FIRE Enthusiasts';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function Image() {
  const iconBuffer = readFileSync(join(process.cwd(), 'app', 'icon.png'));
  const iconDataUri = `data:image/png;base64,${iconBuffer.toString('base64')}`;

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #0891b2 0%, #164e63 100%)',
          color: 'white',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
          <img src={iconDataUri} width={120} height={120} alt="" style={{ borderRadius: 28 }} />
          <span style={{ fontSize: 96, fontWeight: 700 }}>Fireons</span>
        </div>
        <div style={{ display: 'flex', fontSize: 36, marginTop: 28, color: '#cffafe' }}>
          Community for FIRE Enthusiasts
        </div>
      </div>
    ),
    { ...size }
  );
}
