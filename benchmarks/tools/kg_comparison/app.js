'use strict';

const students = JSON.parse(document.getElementById('annotation-data').textContent);
const articles = students[0].records;
const recordMaps = students.map(s => new Map(s.records.map(r => [String(r.index), r])));
const statusNames = {completed: '已完成', in_progress: '进行中', pending: '未开始'};
const typeStyles = {
  Disease: ['疾病', '#9b67b5', '#f5edf9'],
  Symptom: ['症状', '#db9650', '#fff5e8'],
  Medication: ['药物', '#4b91bb', '#eaf5fc'],
  Treatment: ['治疗', '#459b86', '#eaf6f1'],
  'Treatment Plan': ['治疗方案', '#458d6b', '#eef7ec'],
  'Assessment Scale': ['评估量表', '#788ac2', '#f0f2fc'],
  Assessment: ['评估', '#a981b5', '#f5eff9'],
  Examination: ['检查', '#6d9eaa', '#edf6f8'],
  Patient: ['患者', '#bc8496', '#fbf0f3'],
  Risk: ['风险', '#c47770', '#fbefed'],
  Etiology: ['病因', '#a29a54', '#f8f6e9'],
  Evidence: ['证据', '#919ba7', '#f1f4f7'],
  Guideline: ['指南', '#89725a', '#f6f1eb'],
};
const $ = id => document.getElementById(id);
let current = 0;
let graphs = [];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function svgEl(tag, attributes = {}, text) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attributes).forEach(([k, v]) => node.setAttribute(k, v));
  if (text !== undefined) node.textContent = text;
  return node;
}
function button(text, title, action) {
  const node = el('button', '', text);
  node.type = 'button';
  node.title = title;
  node.setAttribute('aria-label', title);
  node.addEventListener('click', action);
  return node;
}
function styleFor(label) { return typeStyles[label] || [label, '#7f8fa2', '#f2f5f8']; }
function textValue(value) { return typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value); }
function relationName(r) { return r.relation_name || r.relation || r.relation_type; }
function wrapName(name) {
  const result = [];
  let line = '';
  let width = 0;
  for (const char of name) {
    const size = /[^\u0000-\u00ff]/.test(char) ? 1.7 : 1;
    if (width + size > 21) { result.push(line.trim()); line = ''; width = 0; }
    line += char; width += size;
  }
  if (line) result.push(line.trim());
  if (result.length > 3) return [...result.slice(0, 2), result[2].slice(0, 19) + '…'];
  return result.length ? result : ['（未命名）'];
}

// A small deterministic force layout; card boundaries include the full node labels.
function layout(entities, relations) {
  const nodes = entities.map((e, i) => {
    const angle = i * 2.39996;
    const radius = 60 + 23 * Math.sqrt(i);
    const lines = wrapName(e.name);
    return {...e, lines, w: 136, h: 31 + lines.length * 13,
      x: 240 + Math.cos(angle) * radius, y: 345 + Math.sin(angle) * radius * 1.6};
  });
  const byId = new Map(nodes.map(n => [n.id, n]));
  const edges = relations.map(r => [byId.get(r.source), byId.get(r.target)]);
  for (let step = 0; step < 320; step++) {
    const force = nodes.map(n => ({x: (240 - n.x) * .0015, y: (345 - n.y) * .0015}));
    const index = new Map(nodes.map((n, i) => [n.id, i]));
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[j].x - nodes[i].x;
        const dy = nodes[j].y - nodes[i].y;
        const distance = Math.max(1, Math.hypot(dx, dy));
        const repulse = 1050 / (distance * distance);
        force[i].x -= dx / distance * repulse;
        force[i].y -= dy / distance * repulse;
        force[j].x += dx / distance * repulse;
        force[j].y += dy / distance * repulse;
      }
    }
    for (const [a, b] of edges) {
      const dx = b.x - a.x, dy = b.y - a.y;
      const distance = Math.max(1, Math.hypot(dx, dy));
      const pull = (distance - 176) * .009;
      const i = index.get(a.id), j = index.get(b.id);
      force[i].x += dx / distance * pull; force[i].y += dy / distance * pull;
      force[j].x -= dx / distance * pull; force[j].y -= dy / distance * pull;
    }
    nodes.forEach((n, i) => { n.x += force[i].x; n.y += force[i].y; });
    for (let pass = 0; pass < 3; pass++) {
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j];
          const dx = b.x - a.x, dy = b.y - a.y;
          const overlapX = (a.w + b.w) / 2 + 20 - Math.abs(dx);
          const overlapY = (a.h + b.h) / 2 + 26 - Math.abs(dy);
          if (overlapX > 0 && overlapY > 0) {
            if (overlapX < overlapY) {
              const move = Math.sign(dx || 1) * overlapX * .51;
              a.x -= move; b.x += move;
            } else {
              const move = Math.sign(dy || 1) * overlapY * .51;
              a.y -= move; b.y += move;
            }
          }
        }
      }
      nodes.forEach(n => {
        n.x = Math.max(n.w / 2 + 18, Math.min(480 - n.w / 2 - 18, n.x));
        n.y = Math.max(n.h / 2 + 24, Math.min(690 - n.h / 2 - 24, n.y));
      });
    }
  }
  return nodes;
}

function graphGeometry(a, b, bend) {
  const dx = b.x - a.x, dy = b.y - a.y;
  const length = Math.max(1, Math.hypot(dx, dy));
  const cx = (a.x + b.x) / 2 - dy / length * bend;
  const cy = (a.y + b.y) / 2 + dx / length * bend;
  function boundary(n, tx, ty, padding) {
    const vx = tx - n.x, vy = ty - n.y;
    const scale = 1 / Math.max(Math.abs(vx) / (n.w / 2 + padding), Math.abs(vy) / (n.h / 2 + padding), .001);
    return {x: n.x + vx * scale, y: n.y + vy * scale};
  }
  const start = boundary(a, cx, cy, 2), end = boundary(b, cx, cy, 6);
  return {path: `M ${start.x} ${start.y} Q ${cx} ${cy} ${end.x} ${end.y}`,
    x: (start.x + 2 * cx + end.x) / 4, y: (start.y + 2 * cy + end.y) / 4 - 5};
}

class GraphPanel {
  constructor(student, record, panelIndex) {
    this.student = student; this.record = record; this.panelIndex = panelIndex;
    this.entities = record.output.entities;
    this.relations = record.output.relations;
    this.nodes = layout(this.entities, this.relations);
    this.byId = new Map(this.nodes.map(n => [n.id, n]));
    this.view = {x: 0, y: 0, w: 480, h: 690};
    this.selected = null;
    this.card = el('article', 'student-card');
    const head = el('header', 'student-header');
    head.append(el('div', 'avatar', student.annotator.name.slice(0, 2)));
    const name = el('div'); name.append(el('h3', '', student.annotator.name));
    name.append(el('div', 'status', `文件状态：${statusNames[record.annotation.status] || record.annotation.status}`));
    const counts = el('div', 'card-counts');
    for (const [value, label] of [[this.entities.length, '实体'], [this.relations.length, '关系']]) {
      const row = el('div'); row.append(el('b', '', value), document.createTextNode(label)); counts.append(row);
    }
    head.append(name, counts); this.card.append(head);
    this.shell = el('div', 'graph-shell');
    const toolbar = el('div', 'graph-toolbar'); toolbar.append(el('span', '', '有向知识图谱'));
    const controls = el('div', 'controls');
    controls.append(button('−', '缩小图谱', () => this.zoom(1.22)), button('+', '放大图谱', () => this.zoom(.82)),
      button('适应', '恢复完整图谱视野', () => this.resetView()));
    if (document.fullscreenEnabled) controls.append(button('⛶', '全屏查看此图谱', () => {
      if (document.fullscreenElement) document.exitFullscreen(); else this.shell.requestFullscreen();
    }));
    toolbar.append(controls); this.shell.append(toolbar);
    this.svg = svgEl('svg', {class: 'graph', role: 'group', 'aria-label': `${student.annotator.name}的知识图谱`});
    const definitions = svgEl('defs');
    const marker = svgEl('marker', {id: `arrow-${panelIndex}`, markerWidth: 7, markerHeight: 7,
      refX: 6, refY: 3.5, orient: 'auto', markerUnits: 'userSpaceOnUse'});
    marker.append(svgEl('path', {d: 'M 0 0 L 7 3.5 L 0 7 Z', fill: '#899db5'}));
    definitions.append(marker); this.svg.append(definitions);
    this.edgeLayer = svgEl('g'); this.nodeLayer = svgEl('g'); this.svg.append(this.edgeLayer, this.nodeLayer);
    this.shell.append(this.svg, el('div', 'graph-hint', this.relations.length ? '箭头表示关系方向' : '本篇标注未包含关系 · 保留全部实体'));
    this.card.append(this.shell);
    this.detail = el('div', 'detail'); this.detail.setAttribute('aria-live', 'polite'); this.card.append(this.detail);
    this.createEdges(); this.createNodes(); this.updateGeometry(); this.updateView(); this.bindPointer(); this.showOverview();
  }
  createEdges() {
    const groups = new Map();
    this.relations.forEach((r, i) => {
      const key = [r.source, r.target].sort().join('|');
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(i);
    });
    this.edgeElements = this.relations.map((r, i) => {
      const group = svgEl('g', {class: 'edge', tabindex: 0, role: 'button', 'aria-label':
        `${this.byId.get(r.source).name}，${relationName(r)}，${this.byId.get(r.target).name}`});
      const line = svgEl('path', {class: 'edge-line', 'marker-end': `url(#arrow-${this.panelIndex})`});
      const hit = svgEl('path', {class: 'edge-hit'});
      const label = svgEl('text', {'text-anchor': 'middle'}, relationName(r));
      group.append(line, hit, label, svgEl('title', {}, `${relationName(r)} (${r.relation})`));
      group.addEventListener('click', () => { if (!this.suppressClick) this.selectEdge(i); });
      group.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.selectEdge(i); } });
      this.edgeLayer.append(group);
      const peers = groups.get([r.source, r.target].sort().join('|'));
      const canonicalBend = (peers.indexOf(i) - (peers.length - 1) / 2) * 52;
      return {group, line, hit, label, bend: canonicalBend * (r.source < r.target ? 1 : -1)};
    });
    this.setEdgeLabels($('edgeLabels').checked);
  }
  createNodes() {
    this.nodeElements = this.nodes.map(n => {
      const [type, color, background] = styleFor(n.label);
      const group = svgEl('g', {class: 'node', tabindex: 0, role: 'button', 'data-node-id': n.id,
        'aria-label': `${n.name}，${type}，${n.id}`});
      group.append(svgEl('rect', {x: -n.w / 2, y: -n.h / 2, width: n.w, height: n.h, rx: 9, fill: background, stroke: color}));
      group.append(svgEl('text', {x: 0, y: -n.h / 2 + 14, class: 'type-label', 'text-anchor': 'middle'}, `${type} · ${n.id}`));
      n.lines.forEach((line, i) => group.append(svgEl('text', {x: 0, y: -n.h / 2 + 29 + i * 13,
        class: 'entity-label', 'text-anchor': 'middle'}, line)));
      group.append(svgEl('title', {}, `${n.name}\n${n.label} · ${n.id}`));
      group.addEventListener('click', () => { if (!this.suppressClick) this.selectNode(n.id); });
      group.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this.selectNode(n.id); } });
      this.nodeLayer.append(group); return group;
    });
  }
  updateGeometry() {
    this.nodes.forEach((n, i) => this.nodeElements[i].setAttribute('transform', `translate(${n.x},${n.y})`));
    this.relations.forEach((r, i) => {
      const edge = this.edgeElements[i];
      const shape = graphGeometry(this.byId.get(r.source), this.byId.get(r.target), edge.bend);
      edge.line.setAttribute('d', shape.path); edge.hit.setAttribute('d', shape.path);
      edge.label.setAttribute('x', shape.x); edge.label.setAttribute('y', shape.y);
    });
  }
  updateView() { const v = this.view; this.svg.setAttribute('viewBox', `${v.x} ${v.y} ${v.w} ${v.h}`); }
  resetView() {
    const minX = Math.min(0, ...this.nodes.map(n => n.x - n.w / 2 - 15));
    const minY = Math.min(0, ...this.nodes.map(n => n.y - n.h / 2 - 15));
    const maxX = Math.max(480, ...this.nodes.map(n => n.x + n.w / 2 + 15));
    const maxY = Math.max(690, ...this.nodes.map(n => n.y + n.h / 2 + 15));
    this.view = {x: minX, y: minY, w: maxX - minX, h: maxY - minY}; this.updateView();
  }
  zoom(factor, point) {
    const v = this.view;
    const width = Math.max(150, Math.min(1800, v.w * factor));
    factor = width / v.w;
    const center = point || {x: v.x + v.w / 2, y: v.y + v.h / 2};
    this.view = {x: center.x - (center.x - v.x) * factor, y: center.y - (center.y - v.y) * factor,
      w: width, h: v.h * factor}; this.updateView();
  }
  pointerPoint(event) {
    const point = this.svg.createSVGPoint(); point.x = event.clientX; point.y = event.clientY;
    return point.matrixTransform(this.svg.getScreenCTM().inverse());
  }
  bindPointer() {
    this.svg.addEventListener('wheel', e => { e.preventDefault(); this.zoom(Math.exp(e.deltaY * .0014), this.pointerPoint(e)); }, {passive: false});
    this.svg.addEventListener('pointerdown', e => {
      if (e.button !== 0) return;
      const group = e.target.closest('.node');
      const node = group ? this.byId.get(group.getAttribute('data-node-id')) : null;
      this.drag = {pointerId: e.pointerId, target: e.target, node, startX: e.clientX, startY: e.clientY, point: this.pointerPoint(e), moved: false};
      this.suppressClick = false;
    });
    this.svg.addEventListener('pointermove', e => {
      if (!this.drag || this.drag.pointerId !== e.pointerId) return;
      const d = this.drag;
      if (!d.moved && Math.hypot(e.clientX - d.startX, e.clientY - d.startY) < 4) return;
      if (!d.moved) { d.moved = true; this.svg.setPointerCapture(e.pointerId); }
      const point = this.pointerPoint(e), dx = point.x - d.point.x, dy = point.y - d.point.y;
      if (d.node) { d.node.x += dx; d.node.y += dy; d.point = point; this.updateGeometry(); }
      else { this.view.x -= dx; this.view.y -= dy; this.updateView(); }
    });
    const finish = e => {
      if (!this.drag || this.drag.pointerId !== e.pointerId) return;
      this.suppressClick = this.drag.moved;
      if (this.svg.hasPointerCapture(e.pointerId)) this.svg.releasePointerCapture(e.pointerId);
      this.drag = null;
    };
    this.svg.addEventListener('pointerup', finish); this.svg.addEventListener('pointercancel', finish);
    this.svg.addEventListener('click', e => {
      if (!this.suppressClick && !e.target.closest('.node,.edge')) this.clearSelection();
    });
    this.svg.addEventListener('keydown', e => { if (e.key === 'Escape') this.clearSelection(); });
  }
  setEdgeLabels(show) { if (this.edgeElements) this.edgeElements.forEach(e => { e.label.style.display = show ? '' : 'none'; }); }
  highlight(nodeIds, edgeIndices, selectedNode, selectedEdge) {
    this.nodeElements.forEach((g, i) => { g.classList.toggle('dimmed', !nodeIds.has(this.nodes[i].id)); g.classList.toggle('selected', this.nodes[i].id === selectedNode); });
    this.edgeElements.forEach((e, i) => { e.group.classList.toggle('dimmed', !edgeIndices.has(i)); e.group.classList.toggle('selected', i === selectedEdge); });
  }
  detailHeader(title) {
    this.detail.replaceChildren();
    this.detail.scrollTop = 0;
    const header = el('div', 'detail-title', title); header.append(button('返回列表', '返回实体和关系列表', () => this.clearSelection())); this.detail.append(header);
  }
  selectNode(id) {
    const node = this.byId.get(id);
    const linkedEdges = new Set(), linkedNodes = new Set([id]);
    this.relations.forEach((r, i) => { if (r.source === id || r.target === id) { linkedEdges.add(i); linkedNodes.add(r.source); linkedNodes.add(r.target); } });
    this.highlight(linkedNodes, linkedEdges, id, null);
    this.detailHeader('实体详情');
    this.detail.append(el('div', 'subtle', `${node.id} · ${node.label} / ${styleFor(node.label)[0]}`), el('h4', '', node.name));
    const fields = Object.entries(node.properties || {});
    if (fields.length) {
      const list = el('dl'); fields.forEach(([k, v]) => list.append(el('dt', '', k), el('dd', '', textValue(v)))); this.detail.append(list);
    } else this.detail.append(el('p', 'subtle', '原文件未填写实体属性。'));
    this.detail.append(el('div', 'detail-title', `相连关系 · ${linkedEdges.size}`));
    linkedEdges.forEach(i => this.detail.append(this.relationButton(i)));
  }
  selectEdge(index) {
    const r = this.relations[index];
    this.highlight(new Set([r.source, r.target]), new Set([index]), null, index);
    this.detailHeader('关系详情');
    this.detail.append(el('h4', '', `${this.byId.get(r.source).name} → ${this.byId.get(r.target).name}`));
    this.detail.append(el('p', '', `${relationName(r)} · ${r.relation}`), el('p', 'subtle', `${r.source} → ${r.target} · ${r.relation_type}`));
    this.detail.append(el('div', 'detail-title', '原文证据'));
    this.detail.append(el('div', 'evidence', r.evidence || '原文件未填写证据。'));
    const extra = Object.entries(r).filter(([key]) => !['source', 'target', 'relation_type', 'relation_name', 'relation', 'evidence'].includes(key));
    if (extra.length) { const list = el('dl'); extra.forEach(([k, v]) => list.append(el('dt', '', k), el('dd', '', textValue(v)))); this.detail.append(list); }
  }
  relationButton(index) {
    const r = this.relations[index];
    const row = button('', '查看关系及原文证据', () => this.selectEdge(index)); row.className = 'relation-row';
    row.append(document.createTextNode(this.byId.get(r.source).name), el('span', '', `↓ ${relationName(r)} · ${r.relation}`), document.createTextNode(this.byId.get(r.target).name));
    return row;
  }
  clearSelection() {
    this.nodeElements.forEach(g => g.classList.remove('dimmed', 'selected'));
    this.edgeElements.forEach(e => e.group.classList.remove('dimmed', 'selected'));
    this.showOverview();
  }
  showOverview(tab = 'entities') {
    this.detail.replaceChildren();
    const tabs = el('div', 'tabbar');
    for (const [key, label] of [['entities', `全部实体 ${this.entities.length}`], ['relations', `全部关系 ${this.relations.length}`], ['notes', '标注备注']]) {
      const control = button(label, label, () => this.showOverview(key));
      if (tab === key) control.classList.add('active'); tabs.append(control);
    }
    this.detail.append(tabs);
    if (tab === 'entities') this.entities.forEach(n => {
      const row = button('', `查看实体 ${n.name}`, () => this.selectNode(n.id)); row.className = 'entity-row';
      row.append(document.createTextNode(n.name), el('small', '', `${n.id} · ${styleFor(n.label)[0]} / ${n.label}`)); this.detail.append(row);
    });
    if (tab === 'relations') {
      this.relations.forEach((r, i) => this.detail.append(this.relationButton(i)));
      if (!this.relations.length) this.detail.append(el('p', 'empty', '原文件未标注关系。'));
    }
    if (tab === 'notes') {
      this.detail.append(el('div', 'subtle', `文件状态：${statusNames[this.record.annotation.status] || this.record.annotation.status}`));
      this.detail.append(el('p', 'note', this.record.annotation.notes || '原文件未填写标注备注。'));
      const notes = this.record.output.extraction_notes;
      if (notes) this.detail.append(el('p', 'note', textValue(notes)));
    }
    this.detail.scrollTop = 0;
  }
}

function renderArticleList() {
  const query = $('search').value.trim().toLowerCase();
  $('articleList').replaceChildren();
  let shown = 0;
  articles.forEach((article, index) => {
    if (query && !`${article.title} ${article.index} ${article.doi || ''}`.toLowerCase().includes(query)) return;
    shown++;
    const link = button('', article.title, () => selectArticle(index)); link.className = 'article-link';
    if (index === current) { link.classList.add('active'); link.setAttribute('aria-current', 'true'); }
    const content = el('div'); content.append(el('span', 'article-short', article.title), el('span', 'article-id', `# ${article.index}`));
    link.append(el('span', 'article-number', String(index + 1).padStart(2, '0')), content); $('articleList').append(link);
  });
  $('articleCount').textContent = `${shown} / ${articles.length}`;
  if (!shown) $('articleList').append(el('p', 'empty', '没有匹配的文章'));
}
function selectArticle(index) {
  current = index;
  const article = articles[index];
  $('articlePosition').textContent = `ARTICLE ${String(index + 1).padStart(2, '0')} / ${articles.length}`;
  $('articleMeta').textContent = `${article.source.toUpperCase()} · # ${article.index}`;
  $('articleTitle').textContent = article.title;
  $('articleDoi').replaceChildren();
  if (article.doi) {
    const link = el('a', '', `DOI: ${article.doi}`); link.href = `https://doi.org/${article.doi}`; link.target = '_blank'; link.rel = 'noopener noreferrer'; $('articleDoi').append(link);
  }
  $('abstractBody').textContent = article.abstract;
  $('previous').disabled = index === 0; $('next').disabled = index === articles.length - 1;
  $('legend').replaceChildren();
  const labels = new Set(students.flatMap((s, i) => recordMaps[i].get(String(article.index)).output.entities.map(e => e.label)));
  Object.keys(typeStyles).filter(type => labels.has(type)).concat([...labels].filter(type => !typeStyles[type])).forEach(type => {
    const [name, color] = styleFor(type); const item = el('span', 'legend-item'); const dot = el('i'); dot.style.background = color;
    item.title = type; item.append(dot, document.createTextNode(name)); $('legend').append(item);
  });
  graphs = students.map((student, i) => new GraphPanel(student, recordMaps[i].get(String(article.index)), i));
  $('board').replaceChildren(...graphs.map(g => g.card)); renderArticleList();
}
function renderSources() {
  const totals = students.map(s => ({entities: s.records.reduce((sum, r) => sum + r.output.entities.length, 0), relations: s.records.reduce((sum, r) => sum + r.output.relations.length, 0)}));
  [[articles.length, '篇文章'], [students.length, '位标注员'], [totals.reduce((sum, t) => sum + t.entities, 0), '个实体']].forEach(([value, label]) => {
    const item = el('span'); item.append(el('b', '', value), document.createTextNode(label)); $('datasetStats').append(item);
  });
  const table = el('table'), head = el('tr');
  ['原始文件', '标注员', '文章数', '实体数', '关系数', '导出时间'].forEach(title => head.append(el('th', '', title)));
  const thead = el('thead'); thead.append(head); table.append(thead); const tbody = el('tbody');
  students.forEach((s, i) => {
    const row = el('tr');
    [s.filename, s.annotator.name, s.records.length, totals[i].entities, totals[i].relations, s.exported_at.replace('T', ' ').replace('Z', ' UTC')].forEach(value => row.append(el('td', '', value)));
    tbody.append(row);
  });
  table.append(tbody); $('sources').append(table);
}

$('search').addEventListener('input', renderArticleList);
$('previous').addEventListener('click', () => { if (current > 0) selectArticle(current - 1); });
$('next').addEventListener('click', () => { if (current < articles.length - 1) selectArticle(current + 1); });
$('edgeLabels').addEventListener('change', () => graphs.forEach(g => g.setEdgeLabels($('edgeLabels').checked)));
$('abstractToggle').addEventListener('click', () => {
  const expanded = $('abstractBody').hidden;
  $('abstractBody').hidden = !expanded;
  $('abstractToggle').setAttribute('aria-expanded', String(expanded));
  $('abstractToggle').textContent = expanded ? '收起原文摘要 ↑' : '展开原文摘要 ↓';
});
renderSources();
selectArticle(0);
