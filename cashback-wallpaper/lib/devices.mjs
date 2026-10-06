// Экраны iPhone в точках (CSS px) при плотности 3x: картинка выходит
// ровно в разрешение экрана, и iOS не растягивает и не режет её.
export const DEVICES = {
  'iphone-17-pro-max': { w: 440, h: 956, label: 'iPhone 17 Pro Max / 16 Pro Max' },
  'iphone-17-pro': { w: 402, h: 874, label: 'iPhone 17 / 17 Pro / 16 Pro' },
  'iphone-air': { w: 420, h: 912, label: 'iPhone Air' },
  'iphone-15-pro-max': { w: 430, h: 932, label: 'iPhone 16 Plus / 15 Pro Max / 15 Plus / 14 Pro Max' },
  'iphone-16': { w: 393, h: 852, label: 'iPhone 16 / 15 / 15 Pro / 14 Pro' },
  'iphone-14': { w: 390, h: 844, label: 'iPhone 16e / 14 / 13 / 12' },
  'iphone-13-mini': { w: 360, h: 780, label: 'iPhone 13 mini / 12 mini' },
};

export const DEFAULT_DEVICE = 'iphone-17-pro-max';
export const DPR = 3;
