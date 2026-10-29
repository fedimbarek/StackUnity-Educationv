import { Component, Input } from '@angular/core';

/** Petit cube isométrique (icône des modules). */
const PALETTES = [
  ['#5aa9ff', '#1a73f0', '#0b4aa8'],
  ['#6fe6d6', '#22b3aa', '#0e6b6e'],
  ['#59617a', '#2e3550', '#1a1f30'],
];

@Component({
  selector: 'app-cube',
  template: `
    <svg viewBox="0 0 64 64" class="cube" aria-hidden="true">
      <polygon points="32,6 56,19 32,32 8,19" [attr.fill]="p()[0]" />
      <polygon points="8,19 32,32 32,58 8,45" [attr.fill]="p()[1]" />
      <polygon points="32,32 56,19 56,45 32,58" [attr.fill]="p()[2]" />
      <polygon points="9,53 15,49 19,55 12,59" fill="#2fd6b4" />
      <polygon points="52,8 57,11 52,14 47,11" fill="#5aa9ff" opacity=".8" />
    </svg>`,
})
export class CubeComponent {
  @Input() i = 0;
  p() { return PALETTES[this.i % PALETTES.length]; }
}

/** Illustration du hero : formes géométriques bleues sur fond sombre. */
@Component({
  selector: 'app-hero-art',
  template: `
    <svg viewBox="0 0 520 440" class="hero-art" aria-hidden="true">
      <defs>
        <linearGradient id="ha1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2d8cff"/><stop offset="1" stop-color="#0a3a8a"/></linearGradient>
        <linearGradient id="ha2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3fd0dc"/><stop offset="1" stop-color="#0d5f86"/></linearGradient>
        <linearGradient id="ha3" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1f7bff"/><stop offset="1" stop-color="#0c47b5"/></linearGradient>
      </defs>
      <polygon points="330,30 505,205 330,380 155,205" fill="url(#ha1)" />
      <polygon points="470,120 520,170 470,250 420,200" fill="url(#ha2)" opacity=".9" />
      <rect x="130" y="110" width="190" height="190" rx="3" fill="#1b2030" stroke="#2b3248" transform="rotate(-4 225 205)" />
      <rect x="300" y="75" width="120" height="120" rx="3" fill="#232a3d" stroke="#2f3850" transform="rotate(14 360 135)" />
      <polygon points="130,215 195,240 175,310 105,285" fill="url(#ha3)" transform="translate(30 20)" />
      <polygon points="130,215 195,240 175,310 105,285" fill="none" stroke="#7bb6ff" stroke-width=".8" transform="translate(30 20)" opacity=".6"/>
      <rect x="95" y="85" width="40" height="40" fill="#222a3e" transform="rotate(18 115 105)" />
      <circle cx="120" cy="260" r="62" fill="none" stroke="#2d364d" />
      <polygon points="215,18 240,38 215,58 190,38" fill="#2d8cff" />
      <polygon points="150,55 160,65 150,75 140,65" fill="#13304f" />
      <circle cx="440" cy="40" r="3" fill="#cfe4ff" /><circle cx="460" cy="26" r="2" fill="#5aa9ff" /><circle cx="485" cy="55" r="2.5" fill="#cfe4ff" />
    </svg>`,
})
export class HeroArtComponent {}
