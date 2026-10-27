// Data compatibility checks only; these do not exercise a browser or page layout.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const {test} = require("node:test");

const root = path.resolve(__dirname, "../../..");
const dataset = path.join(root, "benchmarks/datasets/kg_pilot_20");
const page = fs.readFileSync(path.join(dataset, "pages/kg_annotation_20.html"), "utf8");
const data = JSON.parse(page.match(/<script id="app-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const source = fs.readFileSync(path.join(__dirname, "app.js"), "utf8").split("// Article navigation and workbench controls.")[0];
const jsonCopy = (value) => JSON.parse(JSON.stringify(value));

function workbench(savedState) {
  const errors = [];
  const context = vm.createContext({
    document: {getElementById: (id) => id === "app-data" ? {textContent: JSON.stringify(data)} : {}},
    localStorage: {getItem: () => savedState ? JSON.stringify(savedState) : null},
    alert: (message) => errors.push(message), confirm: () => true,
    setTimeout, clearTimeout,
  });
  vm.runInContext(source + `
    renderIdentity = renderSidebar = renderArticle = persist = clearSelection = toast = () => {};
    globalThis.api = {importedGraph, importJSON, outputFor, buildExport, schemaIssues, definitionForEdge,
      matchingCurrentRule, emptyRecord, getState: () => state};
  `, context);
  return {api: context.api, errors};
}

const oldFiles = fs.readdirSync(path.join(dataset, "annotations")).filter((name) => name.endsWith(".json") && name.includes("20articles"));
for (const filename of oldFiles) {
  test(`preserve all graph content on import/export: ${filename}`, async () => {
    const input = JSON.parse(fs.readFileSync(path.join(dataset, "annotations", filename), "utf8"));
    const {api, errors} = workbench();
    await api.importJSON({text: async () => JSON.stringify(input)});
    assert.deepEqual(errors, []);
    const output = jsonCopy(api.buildExport());
    assert.equal(output.records.length, data.articles.length);
    assert.equal(output.annotator.name, input.annotator.name);
    assert.equal(output.schema.version, "3.1.0");
    for (const before of input.records) {
      const after = output.records.find((r) => r.index === before.index);
      assert.deepEqual(after.output.entities, before.output.entities);
      const meaning = (edge) => ({source: edge.source, target: edge.target, relation: edge.relation, evidence: edge.evidence});
      assert.deepEqual(after.output.relations.map(meaning), before.output.relations.map(meaning));
      assert.equal(after.annotation.notes, before.annotation.notes);
      assert.equal(after.annotation.updated_at, before.annotation.updated_at);
      if (before.output.entities.length) {
        assert.equal(after.annotation.schema_reviewed, false);
        assert.notEqual(after.annotation.status, "completed");
      }
      // A new-version round trip must preserve every unresolved deprecation issue.
      const roundTrip = api.importedGraph(after, "3.1.0");
      assert.deepEqual(jsonCopy(api.schemaIssues(roundTrip)), after.annotation.schema_issues);
    }
    for (const article of data.articles.filter((r) => r.batch === "supplement")) {
      const record = output.records.find((r) => r.index === article.index);
      assert.equal(record.annotation.status, "pending");
      assert.deepEqual(record.output.entities, []);
      assert.deepEqual(record.output.relations, []);
    }
    console.log(JSON.stringify({file: filename, entities: input.records.reduce((n,r)=>n+r.output.entities.length,0),
      relations: input.records.reduce((n,r)=>n+r.output.relations.length,0),
      deprecated_issues: output.records.reduce((n,r)=>n+r.annotation.schema_issues.length,0)}));
  });
}

test("all three annotators coexist and retain their own graphs", async () => {
  const {api, errors} = workbench();
  const inputs = oldFiles.map((name) => JSON.parse(fs.readFileSync(path.join(dataset,"annotations",name),"utf8")));
  for (const input of inputs) await api.importJSON({text:async()=>JSON.stringify(input)});
  assert.deepEqual(errors,[]);
  for (const input of inputs) {
    api.getState().activeReviewer = input.annotator.name;
    const output = jsonCopy(api.buildExport());
    assert.equal(output.annotator.name,input.annotator.name);
    assert.equal(output.summary.entities,input.records.reduce((n,r)=>n+r.output.entities.length,0));
    assert.equal(output.summary.relations,input.records.reduce((n,r)=>n+r.output.relations.length,0));
  }
});

test("measures is current for dimensions and deprecated for diseases; evaluates is current", () => {
  const {api} = workbench();
  const record = {index: data.articles[0].index, output: {
    entities: [{id:"AS1",label:"Assessment Scale",name:"scale",properties:{}},
      {id:"D1",label:"Disease",name:"disease",properties:{}},
      {id:"AD1",label:"Assessment Dimension",name:"quality of life",properties:{Name:"quality of life"}}],
    relations: [
      {source:"AS1",target:"AD1",relation:"measures",evidence:"scale measures quality of life"},
      {source:"AS1",target:"D1",relation:"measures",evidence:"legacy edge"},
      {source:"AS1",target:"D1",relation:"evaluates",evidence:"scale evaluates disease"},
    ]}, annotation: {status:"in_progress"}};
  const imported = api.importedGraph(record, "3.1.0");
  assert.deepEqual(jsonCopy(api.schemaIssues(imported)), [{kind:"relation",index:1,source:"AS1",target:"D1",relation:"measures"}]);
  assert.ok(api.matchingCurrentRule("Treatment Plan", "therapeutically_indicated_for", "Disease"));
  assert.ok(api.matchingCurrentRule("Communication Strategy", "recommended_for", "Patient"));
  assert.equal(api.matchingCurrentRule("Medication", "recommended_for", "Disease"), undefined);
});

test("legacy row keys and local completed progress survive schema upgrade", () => {
  const input = JSON.parse(fs.readFileSync(path.join(dataset, "annotations", oldFiles[0]), "utf8"));
  const {api} = workbench();
  const articles = {};
  for (const record of input.records) {
    const graph = jsonCopy(api.importedGraph(record));
    graph.status = record.annotation.status;
    graph.positions = {M1:{x:123,y:456}};
    const nodes = new Map(graph.entities.map((n)=>[n.id,n]));
    graph.relations.forEach((edge, index) => {
      const old = record.output.relations[index];
      edge.schema_key = data.schema.relations.find((rule) => rule.legacy && rule.source === nodes.get(old.source).label
        && rule.relation === old.relation && rule.targets.includes(nodes.get(old.target).label)).key;
    });
    delete graph.schema_reviewed;
    articles[record.index] = graph;
  }
  const upgraded = workbench({dataset_id:data.dataset_id,activeReviewer:input.annotator.name,activeArticle:3,
    reviewers:{[input.annotator.name]:{articles}}}).api;
  const state = upgraded.getState();
  assert.equal(state.activeArticle, 3);
  const output = jsonCopy(upgraded.buildExport());
  assert.equal(output.records.length, data.articles.length);
  for (const record of Object.values(state.reviewers[input.annotator.name].articles)) {
    assert.deepEqual(jsonCopy(record.positions), {M1:{x:123,y:456}});
    assert.doesNotThrow(()=>upgraded.schemaIssues(record));
    if (record.entities.length) assert.notEqual(record.status,"completed");
  }
});
