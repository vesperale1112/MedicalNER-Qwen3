"use strict";

const DATA = JSON.parse(document.getElementById("app-data").textContent);
const $ = (id) => document.getElementById(id);
const STORAGE_KEY = "medicalner-kg-20-final-schema-v1";
const ANONYMOUS = "未署名";
const NODE_TYPES = new Map(DATA.schema.nodes.map((item) => [item.label, item]));
const EDGE_TYPES = DATA.schema.relations.filter((item) => item.targets.length > 0);
const EDGE_BY_KEY = new Map(EDGE_TYPES.map((item) => [item.key, item]));
const STATUS_NAMES = {pending: "未开始", in_progress: "标注中", completed: "已完成"};
const PREFIXES = {Disease: "D", Symptom: "S", "Diagnostic Criterion": "DC", Assessment: "A", Patient: "P", Medication: "M", Treatment: "T", "Treatment Plan": "TP", Examination: "EX", "Assessment Scale": "AS", Etiology: "ET", Risk: "R", "Communication Strategy": "CS", Guideline: "G", Evidence: "E", "Assessment Dimension": "AD"};
const COLORS = {Disease: "#527fba", Symptom: "#bd8654", "Diagnostic Criterion": "#8b72b2", Assessment: "#638dac", Patient: "#bd7998", Medication: "#298e79", Treatment: "#70904f", "Treatment Plan": "#5d9c96", Examination: "#7b90b1", "Assessment Scale": "#998056", Etiology: "#947765", Risk: "#c2766e", "Communication Strategy": "#a385af", Guideline: "#6c8293", Evidence: "#708d9c", "Assessment Dimension": "#488f98"};
const CURRENT_EDGES = EDGE_TYPES.filter((rule) => !rule.legacy);

function matchingCurrentRule(sourceLabel, relation, targetLabel) {
  return CURRENT_EDGES.find((rule) => rule.source === sourceLabel && rule.relation === relation && rule.targets.includes(targetLabel));
}

function definitionForEdge(edge, record = currentRecord()) {
  const rule = EDGE_BY_KEY.get(edge.schema_key);
  const source = record.entities.find((node) => node.id === edge.source);
  const target = record.entities.find((node) => node.id === edge.target);
  return matchingCurrentRule(source.label, rule.relation, target.label) || rule;
}

function schemaIssues(record) {
  const issues = [];
  record.entities.forEach((node) => {
    const definition = NODE_TYPES.get(node.label);
    if (definition.deprecated) issues.push({kind: "entity", id: node.id, label: node.label});
    Object.keys(node.properties).filter((key) => !definition.properties.includes(key)).forEach((property) => issues.push({kind: "property", id: node.id, property}));
  });
  record.relations.forEach((edge, index) => {
    const rule = definitionForEdge(edge, record);
    if (rule.legacy) issues.push({kind: "relation", index, source: edge.source, target: edge.target, relation: rule.relation});
  });
  return issues;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function option(value, text) {
  const node = element("option", "", text);
  node.value = value;
  return node;
}

function emptyRecord() {
  return {status: "pending", entities: [], relations: [], notes: "", updated_at: null, positions: {}, schema_reviewed: true, previous_status: null};
}

function emptyState() {
  return {dataset_id: DATA.dataset_id, activeReviewer: ANONYMOUS, activeArticle: 0, reviewers: {[ANONYMOUS]: {articles: {}}}};
}

let storageAvailable = true;
let state;
try {
  const saved = localStorage.getItem(STORAGE_KEY);
  state = saved ? JSON.parse(saved) : emptyState();
} catch (error) {
  state = emptyState();
  storageAvailable = false;
}
// Keep the original storage key and row keys so browser-local progress survives the update.
if (state.schema_version !== DATA.schema.version) {
  Object.values(state.reviewers).forEach((profile) => Object.values(profile.articles).forEach((record) => {
    record.previous_status = record.status;
    record.schema_reviewed = !record.entities.length;
    if (record.entities.length && record.status === "completed") record.status = "in_progress";
  }));
  state.schema_version = DATA.schema.version;
}
let activeTab = "graph";
let activeSchemaTab = "nodes";
let selectedText = "";
let editingNodeId = null;
let editingRelationIndex = null;
let nodePropertiesDraft = [];
let viewport = null;
let graphGesture = null;
let toastTimer;
let pendingIdentityAction = null;

function currentArticle() {
  return DATA.articles[state.activeArticle];
}

function currentProfile() {
  return state.reviewers[state.activeReviewer];
}

function articleRecord(index, create = true) {
  const articles = currentProfile().articles;
  if (!articles[index] && create) articles[index] = emptyRecord();
  return articles[index] || emptyRecord();
}

function currentRecord() {
  return articleRecord(currentArticle().index);
}

function toast(message) {
  clearTimeout(toastTimer);
  $("toast").textContent = message;
  $("toast").hidden = false;
  toastTimer = setTimeout(() => { $("toast").hidden = true; }, 3800);
}

function persist() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    storageAvailable = true;
    $("save-indicator").textContent = "已保存 " + new Date().toLocaleTimeString("zh-CN", {hour: "2-digit", minute: "2-digit"});
    $("save-indicator").classList.remove("warning");
  } catch (error) {
    storageAvailable = false;
    $("save-indicator").textContent = "浏览器未能保存，请导出备份";
    $("save-indicator").classList.add("warning");
  }
}

function markModified() {
  const record = currentRecord();
  record.status = "in_progress";
  record.updated_at = new Date().toISOString();
  persist();
  renderSidebar();
  renderStatus();
}

function renderIdentity() {
  const named = state.activeReviewer !== ANONYMOUS;
  $("reviewer-label").textContent = named ? state.activeReviewer : "填写标注人";
  $("reviewer-avatar").textContent = named ? state.activeReviewer.slice(0, 1) : "?";
}

function renderSidebar() {
  const completed = DATA.articles.filter((article) => articleRecord(article.index, false).status === "completed").length;
  $("completed-count").textContent = completed;
  $("progress-percent").textContent = Math.round(completed / DATA.articles.length * 100) + "%";
  $("progress-fill").style.width = completed / DATA.articles.length * 100 + "%";
  const query = $("article-search").value.trim().toLowerCase();
  const filter = $("article-filter").value;
  const batch = $("batch-filter").value;
  const list = $("article-list");
  list.replaceChildren();
  DATA.articles.forEach((article, ordinal) => {
    const record = articleRecord(article.index, false);
    if (filter === "needs_review" ? record.schema_reviewed && !schemaIssues(record).length : filter !== "all" && record.status !== filter) return;
    if (batch !== "all" && article.batch !== batch) return;
    if (query && ![article.title, article.topic, String(article.index)].join(" ").toLowerCase().includes(query)) return;
    const button = element("button", "article-item" + (ordinal === state.activeArticle ? " active" : ""));
    button.type = "button";
    button.setAttribute("aria-label", `${ordinal + 1}. ${article.title}，${STATUS_NAMES[record.status]}`);
    if (ordinal === state.activeArticle) button.setAttribute("aria-current", "page");
    button.append(element("span", "article-index", String(ordinal + 1).padStart(2, "0")));
    const main = element("span", "article-item-main");
    main.append(element("span", "article-item-title", article.title));
    const meta = element("span", "article-item-meta");
    meta.append(element("span", "", (article.batch === "supplement" ? "新增 · " : "原批 · ") + article.topic), element("span", "", record.entities.length ? `${record.entities.length} 节点 · ${record.relations.length} 关系` : "未开始"));
    main.append(meta);
    button.append(main, element("span", "article-item-state " + record.status));
    button.addEventListener("click", () => selectArticle(ordinal));
    list.append(button);
  });
  if (!list.children.length) list.append(element("p", "list-empty", "没有符合条件的文章"));
}

function renderStatus() {
  const status = currentRecord().status;
  $("article-status").textContent = STATUS_NAMES[status];
  $("article-status").className = "status-chip " + status;
  $("complete-button").textContent = status === "completed" ? "↶ 改为标注中" : "✓ 标记本篇完成";
  $("graph-footer-status").textContent = STATUS_NAMES[status];
}

function clearSelection() {
  selectedText = "";
  $("selection-bar").hidden = true;
  window.getSelection()?.removeAllRanges();
}

function selectArticle(ordinal) {
  state.activeArticle = ordinal;
  viewport = null;
  clearSelection();
  persist();
  renderArticle();
  renderSidebar();
}

function renderArticle() {
  const article = currentArticle();
  $("article-number").textContent = `ARTICLE ${String(state.activeArticle + 1).padStart(2, "0")} / ${DATA.articles.length}`;
  $("article-topic").textContent = (article.batch === "supplement" ? "新增 · " : "原批 · ") + article.topic;
  $("article-title").textContent = article.title;
  $("article-source").textContent = article.source;
  $("article-original-index").textContent = "原始索引 " + article.index;
  $("article-doi").textContent = article.doi ? "DOI " + article.doi : "未提供 DOI";
  if (article.doi) $("article-doi").href = "https://doi.org/" + article.doi;
  else $("article-doi").removeAttribute("href");
  $("abstract-text").textContent = article.abstract;
  $("abstract-text").scrollTop = 0;
  $("word-count").textContent = article.abstract.trim().split(/\s+/).length + " words";
  $("previous-article").disabled = state.activeArticle === 0;
  $("next-article").disabled = state.activeArticle === DATA.articles.length - 1;
  $("article-notes").value = currentRecord().notes;
  renderStatus();
  renderEditor();
}

function setTab(tab) {
  activeTab = tab;
  document.querySelectorAll("[data-tab]").forEach((button) => {
    const active = button.dataset.tab === tab;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  ["graph", "nodes", "relations", "json"].forEach((name) => { $(name + "-tab").hidden = name !== tab; });
  if (tab === "graph") renderGraph();
}

function renderEditor() {
  const record = currentRecord();
  $("graph-count").textContent = `${record.entities.length} 节点 · ${record.relations.length} 关系`;
  $("node-tab-count").textContent = record.entities.length;
  $("relation-tab-count").textContent = record.relations.length;
  $("add-relation").disabled = record.entities.length < 2;
  const issues = schemaIssues(record);
  $("schema-review-notice").hidden = record.schema_reviewed && !issues.length;
  $("schema-review-notice").textContent = issues.length
    ? `本篇有 ${issues.length} 处已弃用的实体、属性或关系，请逐项修订。旧内容和证据均已保留；不会自动替换关系含义。`
    : "这篇旧标注待按 v3.1.0 复核。检查后请重新标记完成。";
  renderNodes();
  renderRelations();
  $("json-preview").textContent = JSON.stringify(outputFor(currentArticle(), record), null, 2);
  renderGraph();
}

function renderNodes() {
  const list = $("node-list");
  list.replaceChildren();
  currentRecord().entities.forEach((node) => {
    const card = element("article", "entity-card");
    const top = element("div", "entity-card-top");
    const definition = NODE_TYPES.get(node.label);
    const kind = element("span", "entity-kind", definition.name + " · " + node.label + (definition.deprecated ? "〔已弃用〕" : ""));
    kind.style.color = COLORS[node.label];
    top.append(kind, element("span", "entity-id", node.id));
    card.append(top, element("h4", "", node.name));
    const properties = element("div", "entity-properties");
    Object.entries(node.properties).forEach(([key, value]) => {
      const property = element("div", "entity-property");
      const deprecated = !definition.properties.includes(key);
      property.append(element("strong", deprecated ? "deprecated-text" : "", key + (deprecated ? "〔已弃用〕" : "")), element("span", "", value));
      properties.append(property);
    });
    card.append(properties);
    const actions = element("div", "card-actions");
    const edit = element("button", "button quiet small", "编辑节点");
    edit.type = "button";
    edit.addEventListener("click", () => openNode(node.id));
    actions.append(edit);
    card.append(actions);
    list.append(card);
  });
  if (!list.children.length) list.append(element("div", "list-empty", "还没有节点，点击「＋ 节点」创建。"));
}

function renderRelations() {
  const list = $("relation-list");
  list.replaceChildren();
  const record = currentRecord();
  record.relations.forEach((edge, ordinal) => {
    const source = record.entities.find((node) => node.id === edge.source);
    const target = record.entities.find((node) => node.id === edge.target);
    const definition = definitionForEdge(edge, record);
    const card = element("article", "relation-card");
    const path = element("div", "relation-card-path");
    path.append(element("strong", "", source.name), element("span", "", "→"), element("span", "relation-badge" + (definition.legacy ? " deprecated-text" : ""), definition.name + " · " + definition.relation + (definition.legacy ? "〔已弃用〕" : "")), element("span", "", "→"), element("strong", "", target.name));
    card.append(path, element("blockquote", "", edge.evidence));
    const actions = element("div", "card-actions");
    const edit = element("button", "button quiet small", "编辑关系");
    edit.type = "button";
    edit.addEventListener("click", () => openRelation(ordinal));
    actions.append(edit);
    card.append(actions);
    list.append(card);
  });
  if (!list.children.length) list.append(element("div", "list-empty", "添加节点后，点击「＋ 关系」连接它们。"));
}

function nextNodeId(label) {
  const prefix = PREFIXES[label];
  const ids = new Set(currentRecord().entities.map((node) => node.id));
  let ordinal = 1;
  while (ids.has(prefix + ordinal)) ordinal += 1;
  return prefix + ordinal;
}

function collectPropertyDraft() {
  nodePropertiesDraft = [...$("property-fields").children].map((row) => ({key: row.querySelector("select").value, value: row.querySelector("textarea").value}));
}

function renderPropertyFields() {
  const definition = NODE_TYPES.get($("node-type").value);
  const properties = definition ? [...definition.properties, ...(definition.legacy_properties || [])] : [];
  const fields = $("property-fields");
  fields.replaceChildren();
  nodePropertiesDraft.forEach((item, index) => {
    const row = element("div", "property-field");
    const select = element("select");
    select.setAttribute("aria-label", "属性名称");
    properties.forEach((property) => select.append(option(property, property + (definition.properties.includes(property) ? "" : "〔已弃用〕"))));
    select.value = item.key;
    const input = element("textarea");
    input.rows = 2;
    input.value = item.value;
    input.placeholder = "填写原文信息";
    input.setAttribute("aria-label", item.key + "属性值");
    const remove = element("button", "icon-button", "×");
    remove.type = "button";
    remove.setAttribute("aria-label", "删除该属性");
    remove.addEventListener("click", () => { collectPropertyDraft(); nodePropertiesDraft.splice(index, 1); renderPropertyFields(); });
    row.append(select, input, remove);
    fields.append(row);
  });
  $("property-empty").hidden = nodePropertiesDraft.length > 0;
  $("add-property").disabled = !definition || definition.properties.every((key) => nodePropertiesDraft.some((item) => item.key === key));
}

function openNode(id = null, name = "") {
  editingNodeId = id;
  const node = id ? currentRecord().entities.find((item) => item.id === id) : null;
  $("node-dialog-title").textContent = node ? "编辑节点" : "创建节点";
  $("node-type").value = node ? node.label : "";
  $("node-id").value = node ? node.id : "选择类别后生成";
  $("node-name").value = node ? node.name : name;
  nodePropertiesDraft = node ? Object.entries(node.properties).map(([key, value]) => ({key, value})) : [];
  $("node-type-description").textContent = node ? NODE_TYPES.get(node.label).description : "选择 Excel schema 中的节点类别。";
  $("node-error").textContent = "";
  $("delete-node").hidden = !node;
  renderPropertyFields();
  $("node-dialog").showModal();
  if (!name && !node) $("node-name").focus();
}

function nodeTypeChanged() {
  collectPropertyDraft();
  const definition = NODE_TYPES.get($("node-type").value);
  if (!definition) {
    nodePropertiesDraft = [];
    $("node-id").value = editingNodeId || "选择类别后生成";
    $("node-type-description").textContent = "选择 Excel schema 中的节点类别。";
    renderPropertyFields();
    return;
  }
  nodePropertiesDraft = nodePropertiesDraft.filter((property) => [...definition.properties, ...(definition.legacy_properties || [])].includes(property.key));
  if (!editingNodeId) $("node-id").value = nextNodeId(definition.label);
  $("node-type-description").textContent = definition.description;
  $("node-error").textContent = "";
  renderPropertyFields();
}

function saveNode(event) {
  event.preventDefault();
  collectPropertyDraft();
  const label = $("node-type").value;
  const name = $("node-name").value.trim();
  if (!name) { $("node-error").textContent = "请填写节点名称。"; return; }
  const keys = nodePropertiesDraft.map((property) => property.key);
  if (new Set(keys).size !== keys.length) { $("node-error").textContent = "同一属性出现了多次，请合并到一个属性值中。"; return; }
  const record = currentRecord();
  const id = editingNodeId || $("node-id").value;
  if (editingNodeId) {
    const incompatible = record.relations.find((edge) => {
      const rule = EDGE_BY_KEY.get(edge.schema_key);
      if (edge.source !== id && edge.target !== id) return false;
      const sourceLabel = edge.source === id ? label : record.entities.find((node) => node.id === edge.source).label;
      const targetLabel = edge.target === id ? label : record.entities.find((node) => node.id === edge.target).label;
      return !matchingCurrentRule(sourceLabel, rule.relation, targetLabel)
        && !(rule.source === sourceLabel && rule.targets.includes(targetLabel));
    });
    if (incompatible) { $("node-error").textContent = "该节点已有关系不符合新的节点类别，请先修改或删除相关关系。"; return; }
  }
  const properties = Object.fromEntries(nodePropertiesDraft.filter((property) => property.value.trim()).map((property) => [property.key, property.value.trim()]));
  const node = {id, label, name, properties};
  if (editingNodeId) record.entities[record.entities.findIndex((item) => item.id === id)] = node;
  else record.entities.push(node);
  record.relations.filter((edge) => edge.source === id || edge.target === id).forEach((edge) => {
    edge.schema_key = definitionForEdge(edge, record).key;
  });
  viewport = null;
  markModified();
  $("node-dialog").close();
  renderEditor();
  toast("节点已保存");
}

function deleteNode() {
  const record = currentRecord();
  const node = record.entities.find((item) => item.id === editingNodeId);
  const connected = record.relations.filter((edge) => edge.source === node.id || edge.target === node.id).length;
  if (!confirm(`删除节点「${node.name}」${connected ? `及其 ${connected} 条关联关系` : ""}？`)) return;
  record.entities = record.entities.filter((item) => item.id !== node.id);
  record.relations = record.relations.filter((edge) => edge.source !== node.id && edge.target !== node.id);
  delete record.positions[node.id];
  viewport = null;
  markModified();
  $("node-dialog").close();
  renderEditor();
  toast("节点已删除");
}

function populateRelationTypes(preferredKey = "", preferredTarget = "") {
  const source = currentRecord().entities.find((node) => node.id === $("relation-source").value);
  const choices = source ? CURRENT_EDGES.filter((rule) => rule.source === source.label) : [];
  // A legacy relation is editable without making deprecated types available for new edges.
  const old = EDGE_BY_KEY.get(preferredKey);
  if (source && old?.legacy && old.source === source.label) choices.push(old);
  $("relation-type").replaceChildren();
  $("relation-type").append(option("", choices.length ? "请选择关系" : "该起点类别没有可用关系"));
  choices.forEach((rule) => {
    const status = rule.legacy ? "〔已弃用〕" : "";
    $("relation-type").append(option(rule.key, `${rule.name} · ${rule.relation} ${status}`));
  });
  if (choices.some((rule) => rule.key === preferredKey)) $("relation-type").value = preferredKey;
  populateRelationTargets(preferredTarget);
}

function populateRelationTargets(preferredTarget = "") {
  const rule = EDGE_BY_KEY.get($("relation-type").value);
  const targets = rule ? currentRecord().entities.filter((node) => rule.targets.includes(node.label) && node.id !== $("relation-source").value) : [];
  $("relation-target").replaceChildren();
  $("relation-target").append(option("", !rule ? "先选择关系" : targets.length ? "请选择终点节点" : "请先创建匹配类别的终点节点"));
  targets.forEach((node) => $("relation-target").append(option(node.id, `${node.name} · ${node.label} · ${node.id}`)));
  if (targets.some((node) => node.id === preferredTarget)) $("relation-target").value = preferredTarget;
  $("save-relation").disabled = !rule || !targets.length;
  $("relation-schema-hint").textContent = rule ? `${rule.source} → ${rule.targets.join(" / ")} · v${rule.version} Excel第${rule.row}行${rule.legacy ? "\n已弃用：仅保留用于修订旧标注。请按证据选择新版关系；可能需要先修改节点类别。" : ""}${rule.note ? "\n" + rule.note : ""}` : "请选择已有节点。";
  $("relation-schema-hint").style.whiteSpace = "pre-line";
}

function openRelation(index = null, evidence = "") {
  if (currentRecord().entities.length < 2) { toast("请先创建至少两个节点。"); return; }
  editingRelationIndex = index;
  const edge = index !== null ? currentRecord().relations[index] : null;
  $("relation-dialog-title").textContent = edge ? "编辑关系" : "创建关系";
  $("relation-source").replaceChildren();
  currentRecord().entities.forEach((node) => $("relation-source").append(option(node.id, `${node.name} · ${node.label} · ${node.id}`)));
  if (edge) $("relation-source").value = edge.source;
  else {
    const usable = currentRecord().entities.find((node) => EDGE_TYPES.some((rule) => rule.source === node.label && currentRecord().entities.some((target) => target.id !== node.id && rule.targets.includes(target.label))));
    if (usable) $("relation-source").value = usable.id;
  }
  populateRelationTypes(edge ? definitionForEdge(edge).key : "", edge ? edge.target : "");
  $("relation-evidence").value = edge ? edge.evidence : evidence;
  $("relation-error").textContent = "";
  $("delete-relation").hidden = !edge;
  $("relation-dialog").showModal();
}

function saveRelation(event) {
  event.preventDefault();
  const record = currentRecord();
  const rule = EDGE_BY_KEY.get($("relation-type").value);
  const source = record.entities.find((node) => node.id === $("relation-source").value);
  const target = record.entities.find((node) => node.id === $("relation-target").value);
  const evidence = $("relation-evidence").value.trim();
  if (!rule || !source || !target || rule.source !== source.label || !rule.targets.includes(target.label)) { $("relation-error").textContent = "起点、关系和终点的类别不符合 Excel schema。"; return; }
  if (!evidence) { $("relation-error").textContent = "请填写支持这条关系的摘要原文。"; return; }
  const edge = {source: source.id, target: target.id, schema_key: rule.key, evidence};
  if (editingRelationIndex !== null) record.relations[editingRelationIndex] = edge;
  else record.relations.push(edge);
  markModified();
  $("relation-dialog").close();
  renderEditor();
  toast("关系已保存");
}

function deleteRelation() {
  if (!confirm("删除这条关系？")) return;
  currentRecord().relations.splice(editingRelationIndex, 1);
  markModified();
  $("relation-dialog").close();
  renderEditor();
  toast("关系已删除");
}

const SVG_NS = "http://www.w3.org/2000/svg";
const NODE_WIDTH = 192;
const NODE_HEIGHT = 68;

function svgElement(tag, attributes = {}, text) {
  const item = document.createElementNS(SVG_NS, tag);
  Object.entries(attributes).forEach(([key, value]) => item.setAttribute(key, String(value)));
  if (text !== undefined) item.textContent = text;
  return item;
}

function ensurePositions() {
  const record = currentRecord();
  const columns = Math.max(2, Math.ceil(Math.sqrt(record.entities.length * 1.35)));
  record.entities.forEach((node, ordinal) => {
    if (!record.positions[node.id]) record.positions[node.id] = {x: 70 + (ordinal % columns) * 270, y: 85 + Math.floor(ordinal / columns) * 165};
  });
}

function fitViewport() {
  const record = currentRecord();
  ensurePositions();
  const positions = record.entities.map((node) => record.positions[node.id]);
  if (!positions.length) return {x: 0, y: 0, width: 720, height: 440};
  const minX = Math.min(...positions.map((point) => point.x)) - 65;
  const minY = Math.min(...positions.map((point) => point.y)) - 80;
  const width = Math.max(520, Math.max(...positions.map((point) => point.x)) + NODE_WIDTH - minX + 65);
  const height = Math.max(320, Math.max(...positions.map((point) => point.y)) + NODE_HEIGHT - minY + 70);
  return {x: minX, y: minY, width, height};
}

function applyViewport() {
  $("graph-svg").setAttribute("viewBox", `${viewport.x} ${viewport.y} ${viewport.width} ${viewport.height}`);
}

function renderGraph() {
  const record = currentRecord();
  const svg = $("graph-svg");
  ensurePositions();
  if (!viewport) viewport = fitViewport();
  applyViewport();
  $("graph-empty").hidden = record.entities.length > 0;
  svg.replaceChildren();
  const defs = svgElement("defs");
  const marker = svgElement("marker", {id: "edge-arrow", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse"});
  marker.append(svgElement("path", {d: "M 0 0 L 10 5 L 0 10 z", fill: "#a9bac2"}));
  defs.append(marker);
  svg.append(defs);
  record.relations.forEach((edge, ordinal) => {
    const source = record.positions[edge.source];
    const target = record.positions[edge.target];
    const rule = definitionForEdge(edge, record);
    const group = svgElement("g", {class: "graph-edge" + (rule.legacy ? " deprecated-edge" : ""), "data-edge": ordinal, tabindex: 0, role: "button", "aria-label": "编辑关系 " + rule.name});
    let path;
    let labelX;
    let labelY;
    if (edge.source === edge.target) {
      path = `M ${source.x + 42} ${source.y} C ${source.x + 10} ${source.y - 55}, ${source.x + 182} ${source.y - 55}, ${source.x + 150} ${source.y}`;
      labelX = source.x + NODE_WIDTH / 2;
      labelY = source.y - 38;
    } else {
      const forward = target.x >= source.x;
      const startX = source.x + (forward ? NODE_WIDTH : 0);
      const endX = target.x + (forward ? 0 : NODE_WIDTH);
      const startY = source.y + NODE_HEIGHT / 2;
      const endY = target.y + NODE_HEIGHT / 2;
      const bend = Math.max(60, Math.abs(endX - startX) * .45) * (forward ? 1 : -1);
      const lane = (ordinal % 3 - 1) * 14;
      path = `M ${startX} ${startY} C ${startX + bend} ${startY + lane}, ${endX - bend} ${endY + lane}, ${endX} ${endY}`;
      labelX = (startX + endX) / 2;
      labelY = (startY + endY) / 2 + lane - 7;
    }
    group.append(svgElement("path", {d: path, class: "edge-hit"}), svgElement("path", {d: path, class: "edge-line", "marker-end": "url(#edge-arrow)"}), svgElement("text", {x: labelX, y: labelY, "text-anchor": "middle"}, rule.name + (rule.legacy ? "〔已弃用〕" : "")));
    group.append(svgElement("title", {}, `${rule.relation}\n${edge.evidence}`));
    svg.append(group);
  });
  record.entities.forEach((node) => {
    const point = record.positions[node.id];
    const color = COLORS[node.label];
    const group = svgElement("g", {class: "graph-node", transform: `translate(${point.x} ${point.y})`, "data-node": node.id, tabindex: 0, role: "button", "aria-label": `编辑节点 ${node.name}，${node.label}`});
    group.append(svgElement("rect", {width: NODE_WIDTH, height: NODE_HEIGHT, rx: 9, fill: "#fff", stroke: color, "stroke-opacity": .55, "stroke-width": 1.2}));
    group.append(svgElement("circle", {cx: 14, cy: 16, r: 3, fill: color}));
    group.append(svgElement("text", {x: 24, y: 20, fill: color, "font-size": 9, "font-family": "Segoe UI, sans-serif"}, node.label));
    group.append(svgElement("text", {x: NODE_WIDTH - 11, y: 20, fill: "#a4b3bb", "text-anchor": "end", "font-size": 8, "font-family": "Segoe UI, sans-serif"}, node.id));
    const name = node.name.replace(/\s+/g, " ");
    const first = name.slice(0, 26);
    const second = name.length > 26 ? name.slice(26, 50) + (name.length > 50 ? "…" : "") : "";
    group.append(svgElement("text", {x: 13, y: second ? 40 : 45, fill: "#304e5d", "font-size": 11, "font-family": "Segoe UI, Microsoft YaHei, sans-serif"}, first));
    if (second) group.append(svgElement("text", {x: 13, y: 56, fill: "#304e5d", "font-size": 11, "font-family": "Segoe UI, Microsoft YaHei, sans-serif"}, second));
    group.append(svgElement("title", {}, `${node.name}\n${node.label} · ${node.id}`));
    svg.append(group);
  });
  const legend = $("graph-legend");
  legend.replaceChildren();
  [...new Set(record.entities.map((node) => node.label))].forEach((label) => {
    const item = element("span", "legend-item");
    const dot = element("span", "legend-dot");
    dot.style.background = COLORS[label];
    item.append(dot, document.createTextNode(NODE_TYPES.get(label).name));
    legend.append(item);
  });
}

function graphPoint(event) {
  const point = $("graph-svg").createSVGPoint();
  point.x = event.clientX;
  point.y = event.clientY;
  return point.matrixTransform($("graph-svg").getScreenCTM().inverse());
}

function zoomGraph(factor) {
  if (!viewport) viewport = fitViewport();
  const width = Math.min(6000, Math.max(180, viewport.width * factor));
  const height = viewport.height * width / viewport.width;
  viewport = {x: viewport.x + (viewport.width - width) / 2, y: viewport.y + (viewport.height - height) / 2, width, height};
  applyViewport();
}

function relationSchemaRow(rule) {
  const row = element("tr");
  const source = element("td", "", rule.source);
  if (rule.source !== rule.source_original) source.append(element("div", "muted", "原表：" + rule.source_original));
  const relation = element("td");
  relation.append(element("strong", "", rule.name), element("div", "", ""));
  const code = element("code", "", rule.relation);
  relation.lastChild.append(code);
  const target = element("td", "", rule.targets.length ? rule.targets.join(" / ") : rule.target_text);
  const notes = element("td");
  notes.append(element("div", "schema-status", rule.legacy ? (rule.deprecated ? "已弃用：" + (rule.deprecated_targets.join(" / ") || rule.target_text) : "新版仍保留") : "v3.1.0"), element("div", "muted", rule.note));
  if (rule.rename_suggestion) notes.append(element("div", "muted", "原表重命名建议：" + rule.rename_suggestion));
  row.append(source, relation, target, notes);
  return row;
}

function tableWithHeaders(headers) {
  const table = element("table", "schema-table");
  const head = element("thead");
  const row = element("tr");
  headers.forEach((header) => row.append(element("th", "", header)));
  head.append(row);
  const body = element("tbody");
  table.append(head, body);
  return {table, body};
}

function renderSchema() {
  const content = $("schema-content");
  content.replaceChildren();
  const query = $("schema-search").value.trim().toLowerCase();
  document.querySelectorAll("[data-schema-tab]").forEach((button) => button.classList.toggle("active", button.dataset.schemaTab === activeSchemaTab));
  if (activeSchemaTab === "nodes") {
    const {table, body} = tableWithHeaders(["Label / 类别", "属性", "原表说明"]);
    DATA.schema.nodes.filter((node) => !query || JSON.stringify(node).toLowerCase().includes(query)).forEach((node) => {
      const row = element("tr");
      const label = element("td");
      label.append(element("strong", "", node.name), element("div", "muted", node.label));
      const properties = element("td");
      node.properties.forEach((property) => properties.append(element("span", "property-chip", property)));
      (node.legacy_properties || []).forEach((property) => properties.append(element("span", "property-chip deprecated-text", property + "〔已弃用〕")));
      row.append(label, properties, element("td", "muted", node.description));
      body.append(row);
    });
    content.append(element("p", "schema-rule", "使用 v3.1.0 节点表定义。旧版属性保留供修订，并明确标记已弃用。"), table);
  } else if (activeSchemaTab === "relations") {
    content.append(element("p", "schema-rule", "以 v3.1.0 的60行关系为准。TreatmentPlan / Communication 按节点表名称统一；量表 measures 的终点为 Assessment Dimension，evaluates 的终点为 Disease / Symptom。"));
    const {table, body} = tableWithHeaders(["起点", "关系", "终点 / 属性处理", "原表状态与备注"]);
    CURRENT_EDGES.filter((rule) => !query || JSON.stringify(rule).toLowerCase().includes(query)).forEach((rule) => body.append(relationSchemaRow(rule)));
    content.append(table);
  } else if (activeSchemaTab === "legacy") {
    content.append(element("p", "schema-rule", "这里保留 v3.0.0 原关系定义。已弃用按起点类别＋关系＋终点类别判断；导入时保留节点、属性、关系和证据，不自动改名或改变方向。"));
    const {table, body} = tableWithHeaders(["旧起点", "旧关系", "旧终点 / 属性处理", "兼容状态"]);
    DATA.schema.relations.filter((rule) => rule.legacy && (!query || JSON.stringify(rule).toLowerCase().includes(query))).forEach((rule) => body.append(relationSchemaRow(rule)));
    content.append(table);
  } else {
    DATA.schema.sheets.forEach((sheet) => {
      const matching = sheet.rows.filter((row) => !query || Object.values(row.cells).join(" ").toLowerCase().includes(query));
      if (!matching.length) return;
      const details = element("details", "schema-original");
      details.open = Boolean(query) || sheet.name === "推断说明";
      details.append(element("summary", "", sheet.name));
      const columns = [...new Set(sheet.rows.flatMap((row) => Object.keys(row.cells)))].sort();
      const header = sheet.rows[0].cells;
      const {table, body} = tableWithHeaders(["Excel行", ...columns.map((column) => header[column] || column)]);
      matching.filter((row) => row !== sheet.rows[0]).forEach((entry) => {
        const row = element("tr");
        row.append(element("td", "", entry.row));
        columns.forEach((column) => row.append(element("td", "", entry.cells[column] || "")));
        body.append(row);
      });
      const scroll = element("div", "table-scroll");
      scroll.append(table);
      details.append(scroll);
      content.append(details);
    });
  }
}

function outputFor(article, record) {
  return {
    source_id: "article_" + article.index,
    code: "",
    title: article.title,
    entities: record.entities.map((node) => ({id: node.id, label: node.label, name: node.name, properties: {...node.properties}})),
    relations: record.relations.map((edge) => {
      const rule = definitionForEdge(edge, record);
      const source = record.entities.find((node) => node.id === edge.source);
      const target = record.entities.find((node) => node.id === edge.target);
      return {source: edge.source, target: edge.target, relation_type: `${source.label}-${target.label}`, relation_name: rule.name, relation: rule.relation, evidence: edge.evidence};
    }),
  };
}

function exportRecord(article) {
  const record = articleRecord(article.index, false);
  return {
    index: article.index,
    source: article.source,
    doi: article.doi,
    title: article.title,
    abstract: article.abstract,
    input: article.title + "\n\n" + article.abstract,
    output: outputFor(article, record),
    annotation: {status: record.status, notes: record.notes, updated_at: record.updated_at,
      schema_reviewed: record.schema_reviewed, previous_status: record.previous_status,
      schema_issues: schemaIssues(record)},
  };
}

function buildExport(articles = DATA.articles) {
  const records = articles.map(exportRecord);
  const statusCounts = {pending: 0, in_progress: 0, completed: 0};
  records.forEach((record) => { statusCounts[record.annotation.status] += 1; });
  return {
    format_version: "medicalner-manual-kg-v1",
    dataset_id: DATA.dataset_id,
    annotator: {name: state.activeReviewer},
    exported_at: new Date().toISOString(),
    schema: {version: DATA.schema.version, source: DATA.schema.source, legacy_source: DATA.schema.legacy_source, interpretation: {...DATA.schema.interpretation}},
    summary: {articles: records.length, ...statusCounts, entities: records.reduce((sum, record) => sum + record.output.entities.length, 0), relations: records.reduce((sum, record) => sum + record.output.relations.length, 0)},
    records,
  };
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = element("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function exportJSON(currentOnly = false) {
  if (state.activeReviewer === ANONYMOUS) {
    pendingIdentityAction = () => exportJSON(currentOnly);
    openIdentity();
    return;
  }
  const result = buildExport(currentOnly ? [currentArticle()] : DATA.articles);
  const name = state.activeReviewer.replace(/[\\/:*?"<>|]/g, "_");
  const date = new Date().toISOString().slice(0, 10);
  const filename = currentOnly ? `MedicalNER_${name}_article_${currentArticle().index}_${date}.json` : `MedicalNER_${name}_${result.records.length}articles_v3.1.0_${date}.json`;
  downloadBlob(new Blob([JSON.stringify(result, null, 2) + "\n"], {type: "application/json;charset=utf-8"}), filename);
  toast(`已生成 ${result.records.length} 篇文章的 JSON，已完成 ${result.summary.completed} 篇。`);
}

function openIdentity() {
  $("reviewer-name").value = state.activeReviewer === ANONYMOUS ? "" : state.activeReviewer;
  $("reviewer-names").replaceChildren();
  Object.keys(state.reviewers).filter((name) => name !== ANONYMOUS).forEach((name) => $("reviewer-names").append(option(name, name)));
  $("reviewer-dialog").showModal();
  $("reviewer-name").focus();
}

function saveIdentity(event) {
  event.preventDefault();
  const name = $("reviewer-name").value.trim();
  if (!name || name === ANONYMOUS) { $("reviewer-name").setCustomValidity("请填写你的姓名或学号。"); $("reviewer-name").reportValidity(); return; }
  if (!state.reviewers[name]) {
    state.reviewers[name] = state.activeReviewer === ANONYMOUS ? currentProfile() : {articles: {}};
    if (state.activeReviewer === ANONYMOUS) state.reviewers[ANONYMOUS] = {articles: {}};
  }
  state.activeReviewer = name;
  viewport = null;
  clearSelection();
  persist();
  renderIdentity();
  renderSidebar();
  renderArticle();
  const next = pendingIdentityAction;
  $("reviewer-dialog").close();
  pendingIdentityAction = null;
  if (next) next();
  else toast("已打开「" + name + "」的标注进度");
}

function importedGraph(record, schemaVersion = "3.0.0") {
  const output = record.output;
  if (!output || !Array.isArray(output.entities) || !Array.isArray(output.relations)) throw new Error(`文章 ${record.index} 的 output 格式不完整。`);
  const entities = output.entities.map((node) => {
    const definition = NODE_TYPES.get(node.label);
    if (!definition || typeof node.id !== "string" || !node.id || typeof node.name !== "string" || !node.name.trim()) throw new Error(`文章 ${record.index} 有无效节点。`);
    if (!node.properties || typeof node.properties !== "object" || Array.isArray(node.properties)) throw new Error(`节点 ${node.id} 的 properties 应为对象。`);
    for (const [key, value] of Object.entries(node.properties)) {
      if (![...definition.properties, ...(definition.legacy_properties || [])].includes(key) || typeof value !== "string") throw new Error(`节点 ${node.id} 的属性 ${key} 不符合新版或兼容的旧版 schema。`);
    }
    return {id: node.id, label: node.label, name: node.name, properties: {...node.properties}};
  });
  const byId = new Map(entities.map((node) => [node.id, node]));
  if (byId.size !== entities.length) throw new Error(`文章 ${record.index} 存在重复节点 ID。`);
  const relations = output.relations.map((edge) => {
    const source = byId.get(edge.source);
    const target = byId.get(edge.target);
    const rule = source && target ? EDGE_TYPES.find((item) => item.relation === edge.relation && item.source === source.label && item.targets.includes(target.label)) : null;
    if (!rule || typeof edge.evidence !== "string" || !edge.evidence.trim()) throw new Error(`文章 ${record.index} 有不符合 schema 或缺少证据的关系。`);
    return {source: edge.source, target: edge.target, schema_key: rule.key, evidence: edge.evidence};
  });
  const annotation = record.annotation || {};
  const status = STATUS_NAMES[annotation.status] ? annotation.status : entities.length ? "in_progress" : "pending";
  if (status === "completed" && !entities.length) throw new Error(`文章 ${record.index} 标为已完成，但没有节点。`);
  const reviewed = schemaVersion === DATA.schema.version ? annotation.schema_reviewed !== false : !entities.length;
  return {status: !reviewed && status === "completed" ? "in_progress" : status, entities, relations,
    notes: typeof annotation.notes === "string" ? annotation.notes : "", updated_at: annotation.updated_at || null,
    positions: {}, schema_reviewed: reviewed, previous_status: annotation.previous_status || (reviewed ? null : status)};
}

async function importJSON(file) {
  if (!file) return;
  try {
    const result = JSON.parse(await file.text());
    if (result.dataset_id !== DATA.dataset_id || !Array.isArray(result.records)) throw new Error("请选择本工具导出的整批或单篇 JSON 文件。");
    const name = result.annotator?.name;
    if (typeof name !== "string" || !name.trim() || name === ANONYMOUS) throw new Error("导入文件缺少标注人姓名。");
    const known = new Set(DATA.articles.map((article) => article.index));
    const incoming = {};
    for (const record of result.records) {
      if (!known.has(record.index)) throw new Error(`文章 ${record.index} 不在当前 ${DATA.articles.length} 篇文章中。`);
      if (incoming[record.index]) throw new Error(`导入文件重复包含文章 ${record.index}。`);
      incoming[record.index] = importedGraph(record, result.schema?.version || "3.0.0");
    }
    const existing = state.reviewers[name]?.articles || {};
    const overwrite = Object.keys(incoming).filter((index) => existing[index] && (existing[index].entities.length || existing[index].notes)).length;
    if (overwrite && !confirm(`导入「${name}」的进度将覆盖其 ${overwrite} 篇已有本地标注，是否继续？`)) return;
    state.reviewers[name] = {articles: {...existing, ...incoming}};
    state.activeReviewer = name;
    viewport = null;
    clearSelection();
    persist();
    renderIdentity();
    renderSidebar();
    renderArticle();
    toast(`已导入「${name}」的 ${Object.keys(incoming).length} 篇进度。旧标注已保留，请按 v3.1.0 复核。`);
  } catch (error) {
    alert("无法导入：" + error.message);
  } finally {
    $("import-file").value = "";
  }
}

// Article navigation and workbench controls.
$("article-search").addEventListener("input", renderSidebar);
$("article-filter").addEventListener("change", renderSidebar);
$("batch-filter").addEventListener("change", renderSidebar);
$("previous-article").addEventListener("click", () => selectArticle(state.activeArticle - 1));
$("next-article").addEventListener("click", () => selectArticle(state.activeArticle + 1));
document.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => setTab(button.dataset.tab)));
document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => $(button.dataset.close).close()));
$("add-node").addEventListener("click", () => openNode());
$("empty-add-node").addEventListener("click", () => openNode());
$("add-relation").addEventListener("click", () => openRelation());
$("node-form").addEventListener("submit", saveNode);
$("node-type").addEventListener("change", nodeTypeChanged);
$("delete-node").addEventListener("click", deleteNode);
$("add-property").addEventListener("click", () => {
  collectPropertyDraft();
  const property = NODE_TYPES.get($("node-type").value).properties.find((key) => !nodePropertiesDraft.some((item) => item.key === key));
  if (property) nodePropertiesDraft.push({key: property, value: ""});
  renderPropertyFields();
});
$("relation-form").addEventListener("submit", saveRelation);
$("relation-source").addEventListener("change", () => populateRelationTypes());
$("relation-type").addEventListener("change", () => populateRelationTargets());
$("delete-relation").addEventListener("click", deleteRelation);
$("use-selection-evidence").addEventListener("click", () => {
  if (selectedText) $("relation-evidence").value = selectedText;
  else toast("先在摘要中选中支持关系的原文。");
});
$("complete-button").addEventListener("click", () => {
  const record = currentRecord();
  if (!record.entities.length) { toast("请先创建节点，再标记本篇完成。"); return; }
  if (record.status !== "completed" && schemaIssues(record).length) { toast("本篇还有已弃用的内容，请修订后再标记完成。"); return; }
  record.status = record.status === "completed" ? "in_progress" : "completed";
  record.schema_reviewed = record.status === "completed";
  record.updated_at = new Date().toISOString();
  persist();
  renderStatus();
  renderSidebar();
  renderEditor();
  toast(record.status === "completed" ? "本篇已标记完成" : "本篇已改为标注中");
});
$("article-notes").addEventListener("input", () => { currentRecord().notes = $("article-notes").value; markModified(); });

function captureSelection() {
  const selection = window.getSelection();
  if (!selection || !selection.rangeCount || !$("abstract-text").contains(selection.getRangeAt(0).commonAncestorContainer)) return;
  const text = selection.toString().trim();
  if (!text) return;
  selectedText = text;
  $("selected-text-preview").textContent = text;
  $("selection-bar").hidden = false;
}
document.addEventListener("mouseup", captureSelection);
$("abstract-text").addEventListener("keyup", captureSelection);
$("selection-node").addEventListener("click", () => openNode(null, selectedText));
$("selection-evidence").addEventListener("click", () => openRelation(null, selectedText));
$("clear-selection").addEventListener("click", clearSelection);

// SVG editing: drag nodes, pan the canvas and open editors on click.
$("graph-svg").addEventListener("pointerdown", (event) => {
  if (event.button !== 0 || event.target.closest(".graph-edge")) return;
  const node = event.target.closest(".graph-node");
  const point = graphPoint(event);
  const id = node?.getAttribute("data-node");
  graphGesture = {id, start: {x: point.x, y: point.y}, position: id ? {...currentRecord().positions[id]} : null, viewport: {...viewport}, moved: false, screenX: event.clientX, screenY: event.clientY};
  $("graph-svg").setPointerCapture(event.pointerId);
  event.preventDefault();
});
$("graph-svg").addEventListener("pointermove", (event) => {
  if (!graphGesture) return;
  const point = graphPoint(event);
  if (Math.hypot(event.clientX - graphGesture.screenX, event.clientY - graphGesture.screenY) > 4) graphGesture.moved = true;
  if (!graphGesture.moved) return;
  if (graphGesture.id) {
    currentRecord().positions[graphGesture.id] = {x: graphGesture.position.x + point.x - graphGesture.start.x, y: graphGesture.position.y + point.y - graphGesture.start.y};
    renderGraph();
  } else {
    const matrix = $("graph-svg").getScreenCTM();
    viewport.x = graphGesture.viewport.x - (event.clientX - graphGesture.screenX) / matrix.a;
    viewport.y = graphGesture.viewport.y - (event.clientY - graphGesture.screenY) / matrix.d;
    applyViewport();
  }
});
$("graph-svg").addEventListener("pointerup", (event) => {
  if (!graphGesture) return;
  const gesture = graphGesture;
  graphGesture = null;
  if ($("graph-svg").hasPointerCapture(event.pointerId)) $("graph-svg").releasePointerCapture(event.pointerId);
  if (gesture.moved) persist();
  else if (gesture.id) openNode(gesture.id);
});
$("graph-svg").addEventListener("pointercancel", () => { graphGesture = null; persist(); });
$("graph-svg").addEventListener("click", (event) => {
  const edge = event.target.closest(".graph-edge");
  if (edge) openRelation(Number(edge.getAttribute("data-edge")));
});
$("graph-svg").addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const node = event.target.closest(".graph-node");
  const edge = event.target.closest(".graph-edge");
  if (node) openNode(node.getAttribute("data-node"));
  else if (edge) openRelation(Number(edge.getAttribute("data-edge")));
  if (node || edge) event.preventDefault();
});
$("graph-svg").addEventListener("wheel", (event) => {
  if (!event.ctrlKey) return;
  event.preventDefault();
  zoomGraph(event.deltaY > 0 ? 1.15 : .87);
}, {passive: false});
$("zoom-in").addEventListener("click", () => zoomGraph(.8));
$("zoom-out").addEventListener("click", () => zoomGraph(1.25));
$("reset-view").addEventListener("click", () => { viewport = fitViewport(); applyViewport(); });
$("auto-layout").addEventListener("click", () => { currentRecord().positions = {}; viewport = null; renderGraph(); persist(); });

// Schema reference, identities and portable JSON.
$("schema-button").addEventListener("click", () => { renderSchema(); $("schema-dialog").showModal(); });
$("schema-search").addEventListener("input", renderSchema);
document.querySelectorAll("[data-schema-tab]").forEach((button) => button.addEventListener("click", () => { activeSchemaTab = button.dataset.schemaTab; renderSchema(); }));
$("download-schema").addEventListener("click", () => {
  const bytes = Uint8Array.from(atob(DATA.schema.workbook_base64), (character) => character.charCodeAt(0));
  downloadBlob(new Blob([bytes], {type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}), "schema1026_v3.1.0.xlsx");
});
$("reviewer-button").addEventListener("click", () => { pendingIdentityAction = null; openIdentity(); });
$("reviewer-form").addEventListener("submit", saveIdentity);
$("reviewer-name").addEventListener("input", () => $("reviewer-name").setCustomValidity(""));
$("reviewer-dialog").addEventListener("close", () => { pendingIdentityAction = null; });
$("export-button").addEventListener("click", () => exportJSON());
$("export-current").addEventListener("click", () => exportJSON(true));
$("import-button").addEventListener("click", () => $("import-file").click());
$("import-file").addEventListener("change", () => importJSON($("import-file").files[0]));
$("copy-json").addEventListener("click", async () => {
  const text = $("json-preview").textContent;
  try {
    if (!navigator.clipboard) throw new Error("clipboard unavailable");
    await navigator.clipboard.writeText(text);
    toast("本篇 output 已复制");
  } catch (error) {
    const input = element("textarea");
    input.value = text;
    input.style.position = "fixed";
    input.style.left = "-9999px";
    document.body.append(input);
    input.select();
    const copied = document.execCommand("copy");
    input.remove();
    toast(copied ? "本篇 output 已复制" : "请在 JSON 预览中选中文字复制。");
  }
});

$("node-type").append(option("", "请选择节点类别"));
DATA.schema.nodes.forEach((node) => $("node-type").append(option(node.label, `${node.name} · ${node.label}${node.deprecated ? "〔已弃用〕" : ""}`)));
$("article-total").textContent = DATA.articles.length + " 篇";
$("progress-total").textContent = `/ ${DATA.articles.length} 已完成`;
$("schema-node-count").textContent = DATA.schema.nodes.filter((node) => !node.deprecated).length;
$("schema-relation-count").textContent = CURRENT_EDGES.length;
renderIdentity();
renderSidebar();
renderArticle();
if (!storageAvailable) {
  $("save-indicator").textContent = "浏览器未能读取进度，请使用 JSON 备份";
  $("save-indicator").classList.add("warning");
}
