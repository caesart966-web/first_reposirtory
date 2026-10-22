// Просмотрщик 3D-модели ОВ (И05.09.26-ОВ): один HTML-файл, работает без интернета.
// Данные — window.MODEL (собирает rdsh/model3d.py). Ось z — вверх, метры, начало — пересечение осей 1/А.
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js';

const M = window.MODEL;
const qs = new URLSearchParams(location.search);
const host = document.getElementById('view');

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.setClearColor(0xffffff, 1);
host.appendChild(renderer.domElement);
const labelR = new CSS2DRenderer();
labelR.domElement.className = 'labels';
host.appendChild(labelR.domElement);

const scene = new THREE.Scene();
THREE.Object3D.DEFAULT_UP.set(0, 0, 1);
const camera = new THREE.PerspectiveCamera(30, 1, 0.05, 400);
camera.up.set(0, 0, 1);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.12;
controls.screenSpacePanning = true;

scene.add(new THREE.HemisphereLight(0xffffff, 0xb8bcc4, 2.0));
const sun = new THREE.DirectionalLight(0xffffff, 1.6);
sun.position.set(-20, -30, 40);
scene.add(sun);
const sun2 = new THREE.DirectionalLight(0xffffff, 0.6);
sun2.position.set(30, 20, 15);
scene.add(sun2);

// ---------------------------------------------------------------- материалы
const mats = {};
function mat(sys) {
  if (!mats[sys]) {
    const [r, g, b] = M.systems[sys].rgb;
    mats[sys] = new THREE.MeshStandardMaterial({ color: new THREE.Color(r / 255, g / 255, b / 255),
      roughness: 0.55, metalness: 0.15 });
  }
  return mats[sys];
}
const wallMat = new THREE.MeshStandardMaterial({ color: 0xe4e1da, roughness: 0.95, transparent: true, opacity: 0.13,
  depthWrite: false, side: THREE.DoubleSide });
const slabMat = new THREE.MeshStandardMaterial({ color: 0xd6d1c6, roughness: 0.95, transparent: true, opacity: 0.12,
  depthWrite: false, side: THREE.DoubleSide });
const edgeMat = new THREE.LineBasicMaterial({ color: 0x9aa0a8, transparent: true, opacity: 0.38 });
const grilleMat = {};
function gmat(sys) {
  if (!grilleMat[sys]) {
    grilleMat[sys] = mat(sys).clone();
    grilleMat[sys].color.lerp(new THREE.Color(0xffffff), 0.35);
  }
  return grilleMat[sys];
}
const unitMat = new THREE.MeshStandardMaterial({ color: 0xe5e7eb, roughness: 0.5, metalness: 0.1 });

// ---------------------------------------------------------------- группы (слои)
const groups = {};
function grp(key) {
  if (!groups[key]) { groups[key] = new THREE.Group(); scene.add(groups[key]); }
  return groups[key];
}
const pickables = [];

function prism(outer, holes, z0, z1, material, key, floor) {
  const sh = new THREE.Shape(outer.map(([x, y]) => new THREE.Vector2(x, y)));
  for (const h of holes) sh.holes.push(new THREE.Path(h.map(([x, y]) => new THREE.Vector2(x, y))));
  const g = new THREE.ExtrudeGeometry(sh, { depth: z1 - z0, bevelEnabled: false });
  g.translate(0, 0, z0);
  const m = new THREE.Mesh(g, material);
  m.userData.floor = floor;
  m.renderOrder = 2;
  grp(key).add(m);
  const e = new THREE.LineSegments(new THREE.EdgesGeometry(g, 30), edgeMat);
  e.userData.floor = floor;
  grp(key).add(e);
}
for (const w of M.walls) prism(w.outer, w.holes, w.z0, w.z1, wallMat, 'walls', w.floor);
for (const s of M.slabs) prism(s.outer, s.holes, s.z0, s.z1, slabMat, 'slabs', 2);

const up = new THREE.Vector3(0, 0, 1);
function segMesh(seg, material, ext) {
  const a = new THREE.Vector3(seg[0], seg[1], seg[2]);
  const b = new THREE.Vector3(seg[3], seg[4], seg[5]);
  const w = seg[6], h = seg[7], rect = seg[8];
  const t = b.clone().sub(a);
  const L = t.length();
  if (L < 1e-6) return null;
  t.normalize();
  let u;
  if (Math.abs(t.z) > 0.999) u = new THREE.Vector3(1, 0, 0);
  else u = new THREE.Vector3(-t.y, t.x, 0).normalize();
  const v = new THREE.Vector3().crossVectors(u, t);   // вертикаль сечения
  const geo = rect ? new THREE.BoxGeometry(w, L + 2 * ext, h)
    : new THREE.CylinderGeometry(w / 2, w / 2, L + 2 * ext, 20, 1, false);
  const m = new THREE.Mesh(geo, material);
  const basis = new THREE.Matrix4().makeBasis(u, t, v);
  m.quaternion.setFromRotationMatrix(basis);
  m.position.copy(a).add(b).multiplyScalar(0.5);
  return m;
}

for (const r of M.runs) {
  const g = new THREE.Group();
  g.userData = { info: r, floor: r.floor };
  for (const s of r.segs) {
    const ext = (r.kind === 'duct' || r.kind === 'pipe') ? Math.min(s[6] / 2, 0.13) : 0;
    const m = segMesh(s, mat(r.sys), ext);
    if (m) { m.userData.owner = g; g.add(m); pickables.push(m); }
  }
  grp(r.sys).add(g);
}
for (const bx of M.boxes) {
  const [x0, y0, z0, x1, y1, z1] = bx.b;
  const geo = new THREE.BoxGeometry(x1 - x0, y1 - y0, Math.max(z1 - z0, 0.004));
  let material = mat(bx.sys);
  if (bx.kind === 'grille' || bx.kind === 'cap') material = gmat(bx.sys);
  if (bx.kind === 'unit') material = bx.sys === 'E' ? unitMat : unitMat;
  const m = new THREE.Mesh(geo, material);
  m.position.set((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
  const g = new THREE.Group();
  g.userData = { info: bx, floor: bx.floor };
  m.userData.owner = g;
  g.add(m);
  if (bx.kind === 'unit' || bx.kind === 'ksd' || bx.kind === 'grille') {
    const [r, gg, b] = M.systems[bx.sys].rgb;
    const e = new THREE.LineSegments(new THREE.EdgesGeometry(geo),
      new THREE.LineBasicMaterial({ color: new THREE.Color(r / 255 * 0.7, gg / 255 * 0.7, b / 255 * 0.7) }));
    e.position.copy(m.position);
    g.add(e);
  }
  pickables.push(m);
  grp(bx.sys).add(g);
}

// подписи расходов
for (const lb of M.labels) {
  const d = document.createElement('div');
  d.className = 'lbl';
  const [r, g, b] = M.systems[lb.sys].rgb;
  d.style.color = `rgb(${r},${g},${b})`;
  d.textContent = lb.text;
  const o = new CSS2DObject(d);
  o.position.set(lb.x, lb.y, lb.z);
  o.userData.floor = lb.floor;
  grp('labels').add(o);
}

// ---------------------------------------------------------------- виды
const VIEWS = {
  iso: { pos: [-9, -17, 19], tgt: [10, 8, 3.6], floor: 0 },
  iso2: { pos: [31, -12, 18], tgt: [9.5, 8.5, 3.8], floor: 0 },
  f1: { pos: [-5, -13, 14], tgt: [9.5, 7.6, 2.6], floor: 1 },
  f2: { pos: [-5, -13, 18], tgt: [9.5, 8.2, 6.4], floor: 2 },
  top: { pos: [10, 8.4, 40], tgt: [10, 8.4, 0], floor: 0 },
  topo: { pos: [11.0, 3.2, 7.2], tgt: [16.6, 10.9, 2.9], floor: 1 },
  bath: { pos: [3.0, 12.5, 15.5], tgt: [15.1, 28.4, 0.6], floor: 3 },
  site: { pos: [-16, -22, 34], tgt: [12, 16, 1.5], floor: 0 },
};
let floorSel = 0;
function applyFloor(f) {
  floorSel = f;
  for (const [k, g] of Object.entries(groups)) {
    g.traverse(o => {
      if (o.userData && o.userData.floor !== undefined && o !== g) {
        const fl = o.userData.floor;
        let vis = f === 0 || fl === f;
        if (k === 'walls' && f === 2 && fl === 1) vis = false;
        if (k === 'slabs') vis = f === 0 || f === 2;
        o.visible = vis;
      }
    });
  }
  document.querySelectorAll('[data-floor]').forEach(b => b.classList.toggle('on', +b.dataset.floor === f));
}
function setView(name) {
  const v = VIEWS[name];
  camera.position.set(...v.pos);
  controls.target.set(...v.tgt);
  controls.update();
  applyFloor(v.floor);
  document.querySelectorAll('[data-view]').forEach(b => b.classList.toggle('on', b.dataset.view === name));
}

// ---------------------------------------------------------------- панель
const layerList = [['walls', 'Стены (по АР)'], ['slabs', 'Перекрытие'], ['П', null], ['В', null], ['Н', null], ['X', null],
  ['ВЗ', null], ['В2', null], ['Р', null], ['F', null], ['E', null], ['ВВ', null], ['labels', 'Подписи расходов']];
const box = document.getElementById('layers');
for (const [k, nm] of layerList) {
  if (!groups[k]) continue;
  const id = 'cb_' + k;
  const lab = document.createElement('label');
  const sw = k in M.systems ? `<i style="background:rgb(${M.systems[k].rgb.join(',')})"></i>` : '<i class="none"></i>';
  lab.innerHTML = `<input type="checkbox" id="${id}" checked>${sw}<span>${nm || M.systems[k].name}</span>`;
  box.appendChild(lab);
  lab.querySelector('input').addEventListener('change', e => {
    groups[k].visible = e.target.checked;
    if (k === 'labels') labelR.domElement.style.display = e.target.checked ? '' : 'none';
  });
}
// без бани в модели — без её видов
if (!M.walls.some(w => w.floor === 3) && !M.runs.some(r => r.floor === 3)) {
  document.querySelectorAll('[data-view="bath"],[data-view="site"],[data-floor="3"]').forEach(b => b.remove());
}
document.querySelectorAll('[data-view]').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
document.querySelectorAll('[data-floor]').forEach(b => b.addEventListener('click', () => applyFloor(+b.dataset.floor)));
document.getElementById('toggle').addEventListener('click', () => document.body.classList.toggle('collapsed'));

// выбор элемента — сведения в карточке
const ray = new THREE.Raycaster();
const ndc = new THREE.Vector2();
const card = document.getElementById('card');
let downAt = null;
renderer.domElement.addEventListener('pointerdown', e => { downAt = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', e => {
  if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 5) return;
  const r = renderer.domElement.getBoundingClientRect();
  ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const hit = ray.intersectObjects(pickables.filter(m => m.visible && m.parent.visible && m.parent.parent.visible))[0];
  if (!hit) { card.hidden = true; return; }
  const info = hit.object.userData.owner.userData.info;
  const sys = M.systems[info.sys].name;
  card.innerHTML = `<b>${info.name}</b><span>${sys}</span>` +
    (info.sec ? `<span>Сечение ${info.sec}</span>` : '') +
    (info.L ? `<span>Расход ${info.L} м³/ч</span>` : '') +
    `<span class="dim">отметка ≈ ${(hit.point.z >= 0 ? '+' : '') + hit.point.z.toFixed(3).replace('.', ',')}</span>`;
  card.hidden = false;
});

function resize() {
  const w = host.clientWidth, h = host.clientHeight;
  renderer.setSize(w, h);
  labelR.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();

// параметры адреса — для снимков видов: ?view=iso&labels=0&ui=0&walls=1
setView(qs.get('view') || 'iso');
if (qs.get('labels') === '0') { groups.labels.visible = false; labelR.domElement.style.display = 'none';
  const c = document.getElementById('cb_labels'); if (c) c.checked = false; }
if (qs.get('ui') === '0') document.body.classList.add('noui');
for (const k of ['walls', 'slabs', 'F']) if (qs.get(k) === '0' && groups[k]) { groups[k].visible = false;
  const c = document.getElementById('cb_' + k); if (c) c.checked = false; }

let frames = 0;
renderer.setAnimationLoop(() => {
  controls.update();
  renderer.render(scene, camera);
  labelR.render(scene, camera);
  if (++frames === 3) window.__ready = true;
});
