const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/home/john/.claude/skills/synced/fa81321a-a3eb-4338-a240-6d1135646e13_df9e8ecd-7b66-4016-8d06-32ae062c9c7a/pptx/scripts/apply_theme.js");

const THEME = {
  name: "APIP",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1F2F3D", lt1: "FFFFFF", dk2: "0E5C6B", lt2: "EAF2F4",
    accent1: "0E5C6B", accent2: "D98A2B", accent3: "5B7C8A",
    accent4: "A63D40", accent5: "7FB0B8", accent6: "C9D6DA",
    hlink: "0E5C6B", folHlink: "5B7C8A",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "APIP: Agent Performance Improvement Plans";
pres.author = "John Harney";
const C = pres.SchemeColor;

pres.defineSlideMaster({
  title: "SUMMARY",
  background: { color: "FFFFFF" },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 12.33, h: 0.9,
        fontSize: 26, bold: true, color: C.text1, margin: 0, valign: "middle" } } },
    { placeholder: { options: { name: "subtitle", type: "body", x: 0.5, y: 1.22, w: 12.33, h: 0.35,
        fontSize: 14, color: C.accent3, margin: 0, valign: "top" } } },
    { text: { text: "Harney et al., IEEE International Conference on Agentic AI (ICA) 2026, Kumamoto. Paper #238.",
        options: { x: 0.5, y: 7.05, w: 12.33, h: 0.3, fontSize: 10, color: C.accent3, margin: 0, isTextBox: true } } },
  ],
});

pres.addSection({ title: "Summary" });
const s = pres.addSlide({ masterName: "SUMMARY", sectionTitle: "Summary" });

s.addText("Your Agent is Underperforming: The Case for Agent Performance Improvement Plans", { placeholder: "title" });
s.addText("A governed post-deployment remediation lifecycle for AI agents, adapted from the HR performance improvement plan (PIP).", { placeholder: "subtitle" });

// ---------- Left column: problem + lifecycle ----------
const LX = 0.5, LW = 7.5;
let y = 1.72;

s.addText([
  { text: "The gap. ", options: { bold: true, color: C.accent1 } },
  { text: "Pre-release evaluation is standardized; the response to degradation after deployment is not. 94% of 413 surveyed practitioners report Day-2 issues, and teams patch prompts ad hoc with no record of what was tried or whether it held.", options: { color: C.text1 } },
], { x: LX, y, w: LW, h: 0.72, fontSize: 13, margin: 0, isTextBox: true, valign: "top", objectName: "The gap" });

y = 2.5;
s.addText("The APIP lifecycle", { x: LX, y, w: LW, h: 0.35, fontSize: 16, bold: true, color: C.accent1, margin: 0, isTextBox: true, objectName: "Lifecycle heading" });

const phases = [
  ["1  Trigger", "Two-gate breach of the behavioral contract: effect size and corrected significance"],
  ["2  Attribute", "Map MAST clusters and signatures to one of five failure modes, or abstain"],
  ["3  Plan", "Pick the intervention tier; escalate within the window"],
  ["4  Window", "Bounded remediation; check-ins at 25 / 50 / 75%"],
  ["5  Exit", "Re-measure the contract envelope; re-breach reopens Phase 1"],
];
const pw = 1.44, gap = 0.1, py = 2.88, ph = 1.42;
phases.forEach((p, i) => {
  const x = LX + i * (pw + gap);
  s.addShape(pres.ShapeType.chevron, { x, y: py, w: pw, h: 0.42, fill: { color: i === 4 ? C.accent2 : C.accent1 }, line: { color: C.background1, width: 0 }, objectName: `Phase ${i+1} chevron` });
  s.addText(p[0], { x: x + 0.12, y: py, w: pw - 0.3, h: 0.42, fontSize: 12, bold: true, color: C.background1, margin: 0, valign: "middle", isTextBox: true, objectName: `Phase ${i+1} label` });
  s.addText(p[1], { x, y: py + 0.5, w: pw, h: ph - 0.5, fontSize: 10.5, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: `Phase ${i+1} text` });
});

// Failure modes -> tiers table
y = 4.4;
s.addText("Five failure modes, three intervention tiers", { x: LX, y, w: LW, h: 0.35, fontSize: 16, bold: true, color: C.accent1, margin: 0, isTextBox: true, objectName: "Taxonomy heading" });
const rows = [
  [{ text: "Failure mode", options: { bold: true, color: C.background1, fill: { color: C.accent1 } } },
   { text: "Signal", options: { bold: true, color: C.background1, fill: { color: C.accent1 } } },
   { text: "Starting tier", options: { bold: true, color: C.background1, fill: { color: C.accent1 } } }],
  ["Behavioral drift", "World moves, corpus frozen; stale citations", "Tier 2: retrieval refresh"],
  ["Input brittleness", "Bimodal success clustered by input segment", "Tier 1, else Tier 3 fine-tune"],
  ["Alignment creep", "Tone or policy compliance erodes", "Tier 1: prompt constraints"],
  ["Tool misuse", "Right intent, wrong invocation", "Tier 1 prompt, else Tier 3"],
  ["Exogenous disruption", "Peers degrade after a mesh change", "Mesh protocol"],
];
s.addTable(rows, { x: LX, y: 4.78, w: LW, colW: [1.7, 3.4, 2.4], fontSize: 10.5, color: C.text1,
  border: { type: "solid", color: THEME.colors.accent6, pt: 0.5 }, margin: [0.03, 0.06, 0.03, 0.06], rowH: 0.26, objectName: "Taxonomy table" });

// ---------- Right column: results ----------
const RX = 8.3, RW = 4.53, IN = 0.15, IW = RW - 2 * IN;
s.addShape(pres.ShapeType.roundRect, { x: RX, y: 1.72, w: RW, h: 4.8, fill: { color: C.background2 }, line: { color: C.background2, width: 0 }, rectRadius: 0.12, objectName: "Results card" });
s.addText("Table II. τ²-bench drift cell, seed 13 (ticks)", { x: RX + IN, y: 1.85, w: IW, h: 0.4, fontSize: 13, bold: true, color: C.accent1, margin: 0, isTextBox: true, valign: "middle", objectName: "Table II heading" });

const hdr = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.accent1 }, align: "center" } });
const cell = (t, o = {}) => ({ text: t, options: { align: "center", ...o } });
const t2 = [
  [hdr("Cond."), hdr("Det."), hdr("Act"), hdr("Exit"), hdr("TTR"), hdr("Cyc."), hdr("Outcome")],
  [cell("oracle", { align: "left" }), cell("17"), cell("17"), cell("19"), cell("2"), cell("1"), cell("resolved")],
  [cell("APIP", { align: "left", bold: true }), cell("17"), cell("27"), cell("29"), cell("12"), cell("1"), cell("resolved", { bold: true })],
  [cell("undiagnosed", { align: "left" }), cell("17"), cell("17"), cell("39"), cell("2, 4, 2, n/a"), cell("4"), cell("timeout", { color: C.accent4 })],
  [cell("no-action", { align: "left" }), cell("17"), cell("n/a"), cell("39"), cell("n/a"), cell("1"), cell("timeout", { color: C.accent4 })],
];
s.addTable(t2, { x: RX + IN, y: 2.3, w: IW, colW: [0.9, 0.4, 0.4, 0.4, 0.95, 0.4, 0.78], fontSize: 9.5, color: C.text1,
  border: { type: "solid", color: THEME.colors.accent6, pt: 0.5 }, margin: [0.02, 0.04, 0.02, 0.04], rowH: 0.25, objectName: "Table II" });
s.addText("Det. = two-gate breach, Act = intervention, Exit = exit evaluation, TTR = Exit − Det. (undiagnosed listed per cycle). All conditions share one injection schedule and task stream.", { x: RX + IN, y: 3.62, w: IW, h: 0.5, fontSize: 9, italic: true, color: C.accent3, margin: 0, isTextBox: true, valign: "top", objectName: "Table II caption" });

const stats = [
  ["4 patches, 3 regressions", "Undiagnosed scored 4× better on per-cycle TTR, then timed out indistinguishable from no-action."],
  ["3 of 3 attributions correct", "Every APIP attribution matched the injected failure mode; it abstained when evidence was thin."],
  ["0 peers degraded", "Mesh insertion of a specialist disrupted no one (ChatDev); bounded shared context may be a precondition."],
];
let sy = 4.2;
stats.forEach((st, i) => {
  s.addText(st[0], { x: RX + IN, y: sy, w: IW, h: 0.34, fontSize: 18, bold: true, color: i === 0 ? C.accent2 : C.accent1, margin: 0, isTextBox: true, valign: "middle", objectName: `Stat ${i+1}` });
  s.addText(st[1], { x: RX + IN, y: sy + 0.34, w: IW, h: 0.4, fontSize: 10, color: C.text1, margin: 0, isTextBox: true, valign: "top", objectName: `Stat ${i+1} caption` });
  sy += 0.78;
});

// Takeaway
s.addText([
  { text: "Takeaway: ", options: { bold: true, color: C.accent2 } },
  { text: "recovery means a durable return to contract, not intervention completion or speed. A scorecard that rewards time-to-resolution without durability prefers the worst strategy.", options: { color: C.text1 } },
], { x: 0.5, y: 6.55, w: 12.33, h: 0.44, fontSize: 12, margin: 0, isTextBox: true, valign: "middle", objectName: "Takeaway" });

s.addNotes("One-slide summary of the APIP paper accepted at IEEE ICA 2026 (paper #238). Left: the problem and the five-phase lifecycle plus the failure-mode taxonomy and tier model. Right: Table II (the tau2-bench drift cell) plus the attribution and mesh results. Bottom: the paper's central claim about durability vs speed.");

(async () => {
  const out = "/home/john/fable5/research_papers/papers/apip/deck/APIP_ICA2026_summary.pptx";
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("wrote", out);
})();
