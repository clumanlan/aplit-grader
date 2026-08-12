import { useState, useEffect, useRef } from "react";

const FONTS = `
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Caveat:wght@600;700&family=Inter:wght@400;500;600;700&display=swap');
@keyframes inkSweep {
  0% { transform: translateY(-100%); }
  100% { transform: translateY(100%); }
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
`;

const COLORS = {
  chrome: "#EDEAF6",
  chromeTextStrong: "#241F2E",
  chromeTextMuted: "#4A3F5C",
  card: "#3F3550",
  paper: "#FAF8F4",
  ink: "#241F2E",
  muted: "#8A8095",
  cream: "#F3EFE8",
  strengthDot: "#8FA98F",
  growthDot: "#D4B24C",
};

const TIER = {
  strong: { bg: "#8FA98F", text: "#1E2A20", label: "Strong" },
  solid: { bg: "#D4B24C", text: "#2E2510", label: "Solid" },
  developing: { bg: "#C97B6B", text: "#F5EDE9", label: "Developing" },
  missing: { bg: "#B3261E", text: "#FDEDEA", label: "Missing" },
};
const tierFor = (s) => (s >= 4 ? TIER.strong : s === 3 ? TIER.solid : TIER.developing);

const STATUS_MESSAGES = [
  "Reading the thesis…",
  "Checking the first body paragraph's evidence…",
  "Weighing the reasoning…",
  "Looking at synthesis across paragraphs…",
  "Reading the conclusion…",
];

// ---- Rubric setup data ----
const SETUP_CRITERIA = {
  standalone: [
    { id: "thesis", label: "Thesis" },
    { id: "conclusion", label: "Conclusion" },
  ],
  groups: [
    { group: "Body ¶1", items: [
      { id: "bp1-claim", label: "Claim" },
      { id: "bp1-evidence-1", label: "Evidence 1" },
      { id: "bp1-reasoning-1", label: "Reasoning 1" },
      { id: "bp1-evidence-2", label: "Evidence 2" },
      { id: "bp1-reasoning-2", label: "Reasoning 2" },
      { id: "bp1-synthesis", label: "Synthesis" },
    ]},
    { group: "Body ¶2", items: [
      { id: "bp2-claim", label: "Claim" },
      { id: "bp2-evidence-1", label: "Evidence 1" },
      { id: "bp2-reasoning-1", label: "Reasoning 1" },
      { id: "bp2-evidence-2", label: "Evidence 2" },
      { id: "bp2-reasoning-2", label: "Reasoning 2" },
      { id: "bp2-synthesis", label: "Synthesis" },
    ]},
  ],
};
const LABEL_BY_ID = Object.fromEntries(
  [...SETUP_CRITERIA.standalone, ...SETUP_CRITERIA.groups.flatMap((g) => g.items.map((i) => ({ ...i, group: g.group })))]
    .map((c) => [c.id, c.group ? `${c.group} ${c.label}` : c.label])
);
const CLASSES = ["Period 3 — AP Lit", "Period 5 — AP Lit", "Period 7 — AP Lit"];

// ---- Demo grading data (stands in for the real model output) ----
const RUBRIC = [
  { id: "thesis", label: "Thesis", group: null, score: 3,
    reasoning: "The claim states an arguable position tied directly to the text (the green light as unreachable promise), which clears the bar for a 3. A 4 on this rubric requires the claim to preview a specific analytical throughline rather than a general symbolic reading — this thesis gestures at the private/collective shift but doesn't name it as the essay's actual structure.",
    strengths: ["Clear, defensible claim you can actually argue against.", "Signals both halves of the essay's structure — Gatsby's hope, then the era's — in one sentence."],
    critiques: ["Push past \u201csymbolism matters\u201d to name what's actually at stake.", "Cut \u201cthe heart of\u201d — it's filler that softens an otherwise strong claim."] },

  { id: "bp1-claim", label: "Claim", group: "Body ¶1", score: 4,
    reasoning: "Meets the 4 bar: the claim is specific to this paragraph (Gatsby's romantic hope as identity-defining), arguable on its own, and explicitly subordinate to the thesis rather than a repetition of it.",
    strengths: ["Sharp and arguable.", "Ties directly back to the thesis without just restating it."],
    critiques: ["None — this is model-level for the rubric."] },
  { id: "bp1-evidence-1", label: "Evidence 1", group: "Body ¶1", score: 3,
    reasoning: "The quotation is directly relevant and correctly attributed, satisfying the 3-band requirement. It stays at 3 rather than 4 because the top band expects evidence to be introduced with more precision about who is speaking and why it matters here.",
    strengths: ["Well-chosen quotation, clearly connected to the claim."],
    critiques: ["Consider quoting Gatsby's own words instead of only Nick's narration, for variety.", "Frame the quote with a sharper lead-in rather than dropping straight into it."] },
  { id: "bp1-reasoning-1", label: "Reasoning 1", group: "Body ¶1", score: null, missing: true,
    reasoning: "The rubric requires an explicit reasoning statement connecting each piece of evidence back to the paragraph's claim. No such sentence follows the first piece of evidence — the paragraph moves straight to a second piece of evidence instead. Because there's nothing present to evaluate, this is flagged as missing rather than scored.",
    strengths: [],
    critiques: ["Add a sentence explaining why the reaching-toward-the-water gesture supports the claim that Gatsby has built his identity around this hope.", "Right now the paragraph jumps from evidence straight to more evidence — reasoning is what turns evidence into an argument."] },
  { id: "bp1-evidence-2", label: "Evidence 2", group: "Body ¶1", score: 3,
    reasoning: "A second, distinct piece of support (the mansion and the parties) that triangulates the first quotation rather than repeating it, meeting the 3-band bar for varied evidence. Held at 3 because the connection between this detail and the paragraph's claim is stated rather than shown through close reading of specific word choice.",
    strengths: ["Genuinely different kind of evidence than the first — action/choice rather than physical gesture.", "Strengthens the paragraph by not relying on a single moment."],
    critiques: ["Point to a specific phrase or detail rather than summarizing the mansion/parties in general terms.", "This pairs well with Evidence 1 — say so explicitly, so the reader sees the paragraph building a case rather than listing examples."] },
  { id: "bp1-reasoning-2", label: "Reasoning 2", group: "Body ¶1", score: 2,
    reasoning: "Held at 2 because this reasoning restates what the evidence shows (parties as bait) without explaining why that specific mechanism matters to the paragraph's claim about identity — the 3-band bar requires reasoning that adds interpretation, not just paraphrase.",
    strengths: ["Correctly identifies the parties as strategic rather than social."],
    critiques: ["Push past restating the evidence — explain why organizing his whole life around one possible arrival is what makes this \u2018identity-defining,\u2019 per the claim.", "This is the shortest reasoning in the essay; it needs another sentence to earn its place next to Reasoning 1."] },
  { id: "bp1-synthesis", label: "Synthesis", group: "Body ¶1", score: 2,
    reasoning: "Scored at 2, not 3, because synthesis on this rubric specifically requires connecting the paragraph's claim to something outside the immediate scene. This paragraph's final sentence restates the scene's emotional stakes rather than reaching outward.",
    strengths: ["Correctly links the moment back to this paragraph's own claim."],
    critiques: ["Reach outside the novel — to the 1920s context or a second text — that's what synthesis at this level asks for.", "Right now this paragraph could stand alone in a summary; push past restating the scene."] },

  { id: "bp2-claim", label: "Claim", group: "Body ¶2", score: 4,
    reasoning: "Meets the 4 bar on the same grounds as the Body ¶1 claim, and does it more cleanly — the claim explicitly escalates the argument rather than parallel-repeating paragraph one's structure.",
    strengths: ["The strongest claim in the essay — confident and precise.", "Clearly escalates from paragraph one instead of repeating it."],
    critiques: ["None — this is model-level for the rubric."] },
  { id: "bp2-evidence-1", label: "Evidence 1", group: "Body ¶2", score: 4,
    reasoning: "Unlike Body ¶1's first piece of evidence, this quotation does interpretive work in the choosing itself, which meets the top-band bar for evidence that's integrated rather than dropped in.",
    strengths: ["Well-chosen and smoothly integrated — does real interpretive work rather than decorating the paragraph."],
    critiques: ["None — this is model-level for the rubric."] },
  { id: "bp2-reasoning-1", label: "Reasoning 1", group: "Body ¶2", score: 3,
    reasoning: "Reasoning is logically sound and follows from the evidence, meeting the 3-band bar. Held at 3 rather than 4 because roughly a third of the sentence re-states the claim instead of extending it.",
    strengths: ["Solid, logical line of reasoning that follows directly from the evidence."],
    critiques: ["Cut the restatement of the claim — trust the reader to remember it.", "Spend that space instead on what \u201cwe\u201d specifically implicates about the reader."] },
  { id: "bp2-evidence-2", label: "Evidence 2", group: "Body ¶2", score: 4,
    reasoning: "A second, well-chosen piece of support (the Dutch sailors' first sighting of the continent) that widens the paragraph's scope exactly as the claim promises, meeting the top band for evidence that's purposefully sequenced rather than merely additional.",
    strengths: ["Excellent choice — extends the essay's central image from Gatsby to a founding national moment.", "Placed at the end of the paragraph, which gives it real weight."],
    critiques: ["None — this is model-level for the rubric."] },
  { id: "bp2-reasoning-2", label: "Reasoning 2", group: "Body ¶2", score: 4,
    reasoning: "This reasoning does what Reasoning 1 didn't quite manage — it explains the significance of the evidence (this is a smaller model of a national pattern) rather than restating it, meeting the top-band bar.",
    strengths: ["Correctly identifies that this parallel reframes the whole essay's stakes, not just this paragraph's.", "Confident, precise closing move for the paragraph."],
    critiques: ["None — this is model-level for the rubric."] },
  { id: "bp2-synthesis", label: "Synthesis", group: "Body ¶2", score: 3,
    reasoning: "Reaches outside the immediate scene toward a broader pattern (the American Dream), which is what separates this from the Body ¶1 synthesis score. Held at 3 rather than 4 because the connection is implied through description rather than named directly.",
    strengths: ["Gestures at the American Dream motif — the right instinct."],
    critiques: ["Name \u201cAmerican Dream\u201d explicitly — right now it's implied, which under-sells a strong observation.", "Tie back to paragraph one's private/collective distinction to unify the essay."] },

  { id: "conclusion", label: "Conclusion", group: null, score: 3,
    reasoning: "Accurately synthesizes the essay's two-part argument and ends on a purposeful image, meeting the 3-band bar. Held at 3 rather than 4 because the rubric's top band for Conclusion asks for a stated \u2018so what\u2019 beyond the text, which isn't present here.",
    strengths: ["Restates the two-symbol argument cleanly.", "Ends on a strong, memorable final image."],
    critiques: ["Add one sentence on why this distinction still matters to a reader today.", "Consider moving the final clause earlier and ending on the essay's own claim instead."] },
];

const ESSAY = {
  title: "The Green Light and the Limits of Longing",
  paras: [
    [{ id: "thesis", text: "In The Great Gatsby, Fitzgerald uses the green light at the end of Daisy's dock as a symbol of the unreachable promises at the heart of the American Dream, one that begins as private longing and ends as a verdict on the era itself." }],
    [
      { id: "bp1-claim", text: "In the novel's early chapters, the light functions specifically as a symbol of Gatsby's romantic hope, a single point of meaning he has built an entire identity around reaching. " },
      { id: "bp1-evidence-1", text: "Nick describes Gatsby stretching his arms toward the water, trembling, fixed on a light that is, to anyone else, unremarkable. " },
      { id: "bp1-reasoning-1", missing: true },
      { id: "bp1-evidence-2", text: "The same hope shapes his choices as much as his posture: he buys a mansion directly across the bay from Daisy's dock and fills it nightly with strangers on the chance that she might wander in. " },
      { id: "bp1-reasoning-2", text: "Every party, then, is not really for the guests — it is bait, organized around a single possible arrival, which shows how completely this hope has reorganized his life. " },
      { id: "bp1-synthesis", text: "This private, almost religious hope is what makes his later disillusionment land so hard — the object was never going to survive contact with the person." },
    ],
    [
      { id: "bp2-claim", text: "By the novel's final page, however, Fitzgerald widens the light from Gatsby's private symbol into a verdict on the American Dream itself. " },
      { id: "bp2-evidence-1", text: "The closing lines describe humanity born to keep striving, carried backward by the very past it's trying to outrun, chasing a future that recedes exactly as fast as we approach it. " },
      { id: "bp2-reasoning-1", text: "That widened focus is doing real work: the failure Nick describes is no longer Gatsby's alone, it belongs to anyone who has organized their life around a promise just out of reach. " },
      { id: "bp2-evidence-2", text: "Fitzgerald reaches even further back, invoking the Dutch sailors who first saw the continent itself as a fresh, unclaimed promise. " },
      { id: "bp2-reasoning-2", text: "Placed at the very end, that image reframes everything before it: Gatsby's failed romance becomes a smaller-scale model of a much older American habit of chasing horizons that keep receding. " },
      { id: "bp2-synthesis", text: "In this light, Gatsby's death reads less as a personal tragedy and more as an early case study of a distinctly American form of hope." },
    ],
    [{ id: "conclusion", text: "The green light, then, is not one symbol but two: first Gatsby's, then everyone's, and Fitzgerald's genius is making the second impossible to unsee once he has shown you the first." }],
  ],
};

function useElapsed(running) {
  const [seconds, setSeconds] = useState(0);
  const ref = useRef(null);
  useEffect(() => {
    if (!running) { setSeconds(0); return; }
    ref.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(ref.current);
  }, [running]);
  return seconds;
}

export default function ApLitGrader() {
  // ---- flow state ----
  const [view, setView] = useState("setup"); // setup | paste | loading | graded | error
  const [showBackToTop, setShowBackToTop] = useState(false);

  useEffect(() => {
    if (view !== "graded") {
      setShowBackToTop(false);
      return;
    }
    const onScroll = () => setShowBackToTop(window.scrollY > 400);
    window.addEventListener("scroll", onScroll);
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, [view]);

  // ---- setup fields (also act as the edit buffer) ----
  const [fullEssay, setFullEssay] = useState(true);
  const [selectedCriteria, setSelectedCriteria] = useState(new Set());
  const [promptText, setPromptText] = useState("");
  const [classId, setClassId] = useState("");

  // ---- cached session, once setup is complete ----
  const [session, setSession] = useState(null); // { sections, prompt, classId, setupAt, count }

  // ---- per-essay fields ----
  const [studentName, setStudentName] = useState("");
  const [essayText, setEssayText] = useState("");

  // ---- loading ----
  const [msgIndex, setMsgIndex] = useState(0);
  const elapsed = useElapsed(view === "loading");

  // ---- grading view ----
  const [active, setActive] = useState("thesis");
  const [expandedReasoning, setExpandedReasoning] = useState(new Set());
  const [overrides, setOverrides] = useState({});
  const [disputes, setDisputes] = useState({});
  const [draftMap, setDraftMap] = useState({});
  const [finished, setFinished] = useState(false);
  const [finishedAt, setFinishedAt] = useState(null);

  useEffect(() => {
    if (view !== "loading") return;
    const id = setInterval(() => setMsgIndex((i) => (i + 1) % STATUS_MESSAGES.length), 3200);
    return () => clearInterval(id);
  }, [view]);

  const effScore = (id) => {
    if (overrides[id] !== undefined) return overrides[id];
    const r = RUBRIC.find((x) => x.id === id);
    return r.missing ? 0 : r.score;
  };
  const isMissingDisplay = (id) => overrides[id] === undefined && RUBRIC.find((r) => r.id === id).missing;
  const overall = (RUBRIC.reduce((a, r) => a + effScore(r.id), 0) / RUBRIC.length).toFixed(1);
  const openUnresolvedCount = Object.values(disputes).filter((d) => d.open && !d.resolved).length;
  const correctedCount = Object.keys(overrides).length;
  const acceptedAsIsCount = RUBRIC.length - correctedCount;
  const unaddressedMissingCount = RUBRIC.filter((r) => r.missing && overrides[r.id] === undefined).length;

  // ---- setup actions ----
  const toggleCriterion = (id) => {
    setFullEssay(false);
    setSelectedCriteria((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };
  const canStartSetup = (fullEssay || selectedCriteria.size > 0) && promptText.trim() && classId;

  const startSession = () => {
    setSession({
      sections: fullEssay ? "Full essay" : [...selectedCriteria].map((id) => LABEL_BY_ID[id]).join(", "),
      prompt: promptText.trim(),
      classId,
      setupAt: new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }),
      count: session ? session.count : 0,
    });
    setView("paste");
  };

  const newAssignment = () => {
    setFullEssay(true);
    setSelectedCriteria(new Set());
    setPromptText("");
    setClassId("");
    setSession(null);
    setStudentName("");
    setEssayText("");
    setView("setup");
  };

  // ---- per-essay actions ----
  const resetEssayGradingState = () => {
    setActive("thesis");
    setExpandedReasoning(new Set());
    setOverrides({});
    setDisputes({});
    setDraftMap({});
    setFinished(false);
    setFinishedAt(null);
  };

  const startGrading = () => {
    if (!studentName.trim() || !essayText.trim()) return;
    resetEssayGradingState();
    setMsgIndex(0);
    setView("loading");
    setTimeout(() => setView("graded"), 5000);
  };

  const retryGrading = () => {
    setMsgIndex(0);
    setView("loading");
    setTimeout(() => setView("graded"), 5000);
  };

  const nextEssay = () => {
    setStudentName("");
    setEssayText("");
    resetEssayGradingState();
    setView("paste");
  };

  // ---- dispute actions ----
  const toggleReasoning = (id) => {
    setExpandedReasoning((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const openDispute = (id) => setDisputes((d) => ({ ...d, [id]: { ...(d[id] || { messages: [] }), open: true } }));

  const sendMessage = (id) => {
    const text = (draftMap[id] || "").trim();
    if (!text) return;
    const teacherMsg = { role: "teacher", text };
    setDraftMap((d) => ({ ...d, [id]: "" }));
    setDisputes((d) => {
      const prev = d[id] || { messages: [], open: true };
      return { ...d, [id]: { ...prev, open: true, messages: [...prev.messages, teacherMsg], sending: true } };
    });
    setTimeout(() => {
      const criterion = RUBRIC.find((r) => r.id === id);
      const claudeMsg = criterion.missing
        ? {
            role: "claude",
            text: `I looked again, and I still don't see a sentence in the essay that does this — the paragraph goes straight from the first piece of evidence to the second without explaining either one. If you're reading it differently, tell me where you see it and I'll take another look. Otherwise, the options are to keep this flagged as missing, or assign a floor score of 1/4 since nothing here meets the rubric's bar.`,
            proposed: 1,
          }
        : (() => {
            const proposed = Math.max(1, effScore(id) - 1);
            return {
              role: "claude",
              text: `You're right to push on this — re-reading ${criterion.label.toLowerCase()} against the rubric's own boundary, I weighted it too generously. I'd put this at ${proposed}/4 instead. Does that match what you're seeing, or is there a different point you'd push back on?`,
              proposed,
            };
          })();
      setDisputes((d) => {
        const prev = d[id];
        return { ...d, [id]: { ...prev, messages: [...prev.messages, claudeMsg], sending: false, pick: claudeMsg.proposed } };
      });
    }, 900);
  };

  const saveCorrection = (id) => {
    const dispute = disputes[id];
    if (!dispute || dispute.pick == null) return;
    setOverrides((o) => ({ ...o, [id]: dispute.pick }));
    setDisputes((d) => ({ ...d, [id]: { ...d[id], resolved: true } }));
  };

  const keepOriginal = (id) => {
    setDisputes((d) => ({ ...d, [id]: { ...d[id], resolved: true } }));
  };

  const finishGrading = () => {
    if (openUnresolvedCount > 0) return;
    setFinished(true);
    setFinishedAt(new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }));
    setSession((s) => ({ ...s, count: s.count + 1 }));
  };

  // ---- shared: cached session bar ----
  const SessionBar = () => (
    <div className="rounded px-5 py-4 mb-6" style={{ background: COLORS.card }}>
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-xs uppercase tracking-wide mb-1" style={{ fontFamily: "'Inter', sans-serif", color: "#C9BFDA" }}>
            Set up {session.setupAt} · {session.count} essay{session.count === 1 ? "" : "s"} graded
          </p>
          <div className="flex gap-2 flex-wrap">
            <span className="px-2.5 py-1 rounded text-xs font-semibold" style={{ fontFamily: "'Inter', sans-serif", background: "rgba(255,255,255,0.12)", color: COLORS.cream }}>
              {session.sections}
            </span>
            <span className="px-2.5 py-1 rounded text-xs font-semibold" style={{ fontFamily: "'Inter', sans-serif", background: "rgba(255,255,255,0.12)", color: COLORS.cream }}>
              {session.classId}
            </span>
            <span
              className="px-2.5 py-1 rounded text-xs font-semibold truncate max-w-xs"
              style={{ fontFamily: "'Inter', sans-serif", background: "rgba(255,255,255,0.12)", color: COLORS.cream }}
              title={session.prompt}
            >
              {session.prompt.length > 40 ? session.prompt.slice(0, 40) + "…" : session.prompt}
            </span>
          </div>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <button onClick={() => setView("setup")} className="text-xs px-3 py-1.5 rounded font-semibold" style={{ fontFamily: "'Inter', sans-serif", background: "rgba(255,255,255,0.12)", color: COLORS.cream }}>
            Adjust assignment
          </button>
          <button onClick={newAssignment} className="text-xs px-3 py-1.5 rounded font-semibold" style={{ fontFamily: "'Inter', sans-serif", background: COLORS.cream, color: COLORS.card }}>
            New assignment
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen w-full" style={{ background: COLORS.chrome }}>
      <style>{FONTS}</style>

      <div className="border-b" style={{ borderColor: "rgba(36,31,46,0.08)" }}>
        <div className="max-w-6xl mx-auto px-6 py-3">
          <span className="text-xs tracking-[0.18em] uppercase" style={{ fontFamily: "'Inter', sans-serif", color: COLORS.chromeTextStrong, fontWeight: 700 }}>
            AP Lit Essay Grader
          </span>
        </div>
      </div>

      <div className={view === "setup" ? "max-w-3xl mx-auto px-6 py-10" : view === "graded" ? "max-w-6xl mx-auto px-6 py-10" : "max-w-5xl mx-auto px-6 py-10"}>

        {/* ---------------- SETUP ---------------- */}
        {view === "setup" && (
          <div className="rounded px-8 py-8 shadow-sm" style={{ background: COLORS.paper, color: COLORS.ink }}>
            <p className="text-xs uppercase tracking-[0.15em] mb-1" style={{ fontFamily: "'Inter', sans-serif", color: COLORS.muted }}>
              {session ? "Edit assignment" : "New assignment"}
            </p>
            <h1 className="mb-1" style={{ fontFamily: "'Fraunces', serif", fontSize: "1.75rem", fontWeight: 600 }}>
              Set this up once
            </h1>
            <p className="mb-8 text-sm" style={{ fontFamily: "'Inter', sans-serif", color: COLORS.muted }}>
              This stays the same for every essay in this batch. You can change it anytime from the grading screen.
            </p>

            <div className="mb-8">
              <p className="text-xs uppercase tracking-wide mb-3 font-semibold" style={{ fontFamily: "'Inter', sans-serif", color: COLORS.ink }}>
                1 · What are we grading?
              </p>
              <div className="inline-flex rounded p-3 mb-3 gap-4 flex-wrap items-center" style={{ background: "#F0ECE3" }}>
                <button
                  onClick={() => { setFullEssay(true); setSelectedCriteria(new Set()); }}
                  className="px-4 py-2 rounded text-sm font-semibold"
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    background: fullEssay ? COLORS.card : "transparent",
                    color: fullEssay ? COLORS.cream : COLORS.ink,
                    border: `1px solid ${fullEssay ? COLORS.card : "#D9D2C4"}`,
                  }}
                >
                  Full essay
                </button>
                <span className="text-xs" style={{ fontFamily: "'Inter', sans-serif", color: COLORS.muted }}>
                  or pick specific criteria →
                </span>
              </div>

              <div className="rounded p-4 space-y-3" style={{ background: "#F0ECE3", opacity: fullEssay ? 0.45 : 1, transition: "opacity 0.2s" }}>
                <div className="flex gap-2 flex-wrap">
                  {SETUP_CRITERIA.standalone.map((c) => (
                    <button
                      key={c.id}
                      onClick={() => toggleCriterion(c.id)}
                      className="px-3 py-1.5 rounded text-sm font-medium"
                      style={{
                        fontFamily: "'Inter', sans-serif",
                        background: selectedCriteria.has(c.id) ? COLORS.card : "white",
                        color: selectedCriteria.has(c.id) ? COLORS.cream : COLORS.ink,
                        border: "1px solid #D9D2C4",
                      }}
                    >
                      {c.label}
                    </button>
                  ))}
                </div>
                {SETUP_CRITERIA.groups.map((g) => (
                  <div key={g.group}>
                    <p className="text-xs uppercase tracking-wide mb-1.5" style={{ fontFamily: "'Inter', sans-serif", color: COLORS.muted }}>
                      {g.group}
                    </p>
                    <div className="flex gap-2 flex-wrap">
                      {g.items.map((c) => (
                        <button
                          key={c.id}
                          onClick={() => toggleCriterion(c.id)}
                          className="px-3 py-1.5 rounded text-sm font-medium"
                          style={{
                            fontFamily: "'Inter', sans-serif",
                            background: selectedCriteria.has(c.id) ? COLORS.card : "white",
                            color: selectedCriteria.has(c.id) ? COLORS.cream : COLORS.ink,
                            border: "1px solid #D9D2C4",
                          }}
                        >
                          {c.label}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="mb-8">
              <p className="text-xs uppercase tracking-wide mb-3 font-semibold" style={{ fontFamily: "'Inter', sans-serif", color: COLORS.ink }}>
                2 · Assignment prompt
              </p>
              <textarea
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
                placeholder="e.g. Analyze how Fitzgerald uses a symbol to develop a theme in The Great Gatsby."
                rows={3}
                className="w-full px-3 py-2.5 rounded text-sm outline-none resize-none"
                style={{ fontFamily: "'Inter', sans-serif", background: "#F0ECE3", color: COLORS.ink, border: "1px solid #D9D2C4" }}
              />
            </div>

            <div className="mb-9">
              <p className="text-xs uppercase tracking-wide mb-3 font-semibold" style={{ fontFamily: "'Inter', sans-serif", color: COLORS.ink }}>
                3 · Class
              </p>
              <select
                value={classId}
                onChange={(e) => setClassId(e.target.value)}
                className="w-full px-3 py-2.5 rounded text-sm outline-none"
                style={{ fontFamily: "'Inter', sans-serif", background: "#F0ECE3", color: COLORS.ink, border: "1px solid #D9D2C4" }}
              >
                <option value="">Choose a class…</option>
                {CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            <div className="flex justify-end gap-3">
              {session && (
                <button onClick={() => setView("paste")} className="text-sm px-4 py-2 rounded font-semibold" style={{ fontFamily: "'Inter', sans-serif", color: COLORS.muted }}>
                  Cancel
                </button>
              )}
              <button
                disabled={!canStartSetup}
                onClick={startSession}
                className="text-sm px-5 py-2.5 rounded uppercase tracking-wide font-semibold"
                style={{
                  fontFamily: "'Inter', sans-serif",
                  background: COLORS.card,
                  color: COLORS.cream,
                  opacity: canStartSetup ? 1 : 0.35,
                  cursor: canStartSetup ? "pointer" : "not-allowed",
                }}
              >
                {session ? "Save changes" : "Start grading"}
              </button>
            </div>
          </div>
        )}

        {/* ---------------- PASTE / LOADING / ERROR ---------------- */}
        {(view === "paste" || view === "loading" || view === "error") && session && (
          <>
            <SessionBar />
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-8">
              <div className="relative rounded px-10 py-12 shadow-sm overflow-hidden" style={{ background: COLORS.paper, color: COLORS.ink }}>
                {view === "loading" && (
                  <div className="absolute left-0 top-0 bottom-0 w-1 overflow-hidden" style={{ background: "rgba(63,53,80,0.12)" }}>
                    <div className="w-full h-1/3" style={{ background: COLORS.card, animation: "inkSweep 1.8s ease-in-out infinite" }} />
                  </div>
                )}

                {view === "paste" && (
                  <>
                    <p className="text-xs uppercase tracking-[0.15em] mb-2" style={{ fontFamily: "'Inter', sans-serif", color: COLORS.muted }}>
                      New essay
                    </p>
                    <h1 className="mb-6" style={{ fontFamily: "'Fraunces', serif", fontSize: "1.75rem", fontWeight: 600 }}>
                      Next essay
                    </h1>
                    <input
                      value={studentName}
                      onChange={(e) => setStudentName(e.target.value)}
                      placeholder="Student name"
                      className="w-full mb-3 px-3 py-2.5 rounded text-sm outline-none"
                      style={{ fontFamily: "'Inter', sans-serif", background: "#F0ECE3", color: COLORS.ink, border: "1px solid #D9D2C4" }}
                    />
                    <textarea
                      value={essayText}
                      onChange={(e) => setEssayText(e.target.value)}
                      placeholder="Paste the essay text here…"
                      rows={12}
                      className="w-full px-4 py-4 rounded outline-none resize-none"
                      style={{ fontFamily: "'Fraunces', serif", fontSize: "1.0625rem", lineHeight: 1.7, background: "#F0ECE3", color: COLORS.ink, border: "1px solid #D9D2C4" }}
                    />
                    <div className="flex justify-end mt-5">
                      <button
                        disabled={!studentName.trim() || !essayText.trim()}
                        onClick={startGrading}
                        className="text-sm px-5 py-2.5 rounded uppercase tracking-wide font-semibold"
                        style={{
                          fontFamily: "'Inter', sans-serif",
                          background: COLORS.card,
                          color: COLORS.cream,
                          opacity: studentName.trim() && essayText.trim() ? 1 : 0.35,
                          cursor: studentName.trim() && essayText.trim() ? "pointer" : "not-allowed",
                        }}
                      >
                        Grade this essay
                      </button>
                    </div>
                  </>
                )}

                {(view === "loading" || view === "error") && (
                  <>
                    <p className="text-xs uppercase tracking-[0.15em] mb-2" style={{ fontFamily: "'Inter', sans-serif", color: COLORS.muted }}>
                      {studentName || "Student"} · {session.classId}
                    </p>
                    <h1 className="mb-8" style={{ fontFamily: "'Fraunces', serif", fontSize: "1.75rem", fontWeight: 600, lineHeight: 1.2 }}>
                      {session.prompt}
                    </h1>
                    <div
                      style={{
                        fontFamily: "'Fraunces', serif",
                        fontSize: "1.0625rem",
                        lineHeight: 1.85,
                        whiteSpace: "pre-line",
                        opacity: view === "loading" ? 0.45 : 0.6,
                      }}
                    >
                      {essayText}
                    </div>
                  </>
                )}
              </div>

              <div className="lg:sticky lg:top-8 self-start">
                {view === "paste" && (
                  <div className="rounded px-4 py-6 text-sm text-center" style={{ background: "rgba(63,53,80,0.06)", color: COLORS.chromeTextMuted, fontFamily: "'Inter', sans-serif" }}>
                    Scores and comments will appear here, next to the lines they refer to, once you grade the essay.
                  </div>
                )}

                {view === "loading" && (
                  <div className="rounded px-5 py-5" style={{ background: COLORS.card }}>
                    <p className="text-xs uppercase tracking-wide mb-3" style={{ fontFamily: "'Inter', sans-serif", color: "#C9BFDA" }}>
                      Grading in progress
                    </p>
                    <p key={msgIndex} style={{ fontFamily: "'Inter', sans-serif", color: COLORS.cream, fontSize: "0.9375rem", lineHeight: 1.6, animation: "fadeIn 0.4s ease-out" }}>
                      {STATUS_MESSAGES[msgIndex]}
                    </p>
                    <div className="mt-4 pt-4 flex items-center justify-between" style={{ borderTop: "1px solid rgba(255,255,255,0.12)" }}>
                      <span className="text-xs" style={{ fontFamily: "'Inter', sans-serif", color: "rgba(255,255,255,0.55)" }}>
                        {elapsed}s elapsed
                      </span>
                      {elapsed >= 20 && (
                        <span className="text-xs text-right" style={{ fontFamily: "'Inter', sans-serif", color: "rgba(255,255,255,0.55)", maxWidth: 160 }}>
                          First grade of a session can take up to a minute.
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {view === "error" && (
                  <div className="rounded px-5 py-5" style={{ background: COLORS.card }}>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: "#C97B6B" }} />
                      <p className="text-xs uppercase tracking-wide" style={{ fontFamily: "'Inter', sans-serif", color: "#E3B7AB" }}>
                        Grading failed
                      </p>
                    </div>
                    <p style={{ fontFamily: "'Inter', sans-serif", color: COLORS.cream, fontSize: "0.9375rem", lineHeight: 1.6 }}>
                      The grading model didn't respond in time. Nothing was lost — the essay is still here.
                    </p>
                    <button
                      onClick={retryGrading}
                      className="mt-4 text-xs px-3 py-2 rounded uppercase tracking-wide font-semibold w-full"
                      style={{ fontFamily: "'Inter', sans-serif", background: "#C97B6B", color: "#2E1712" }}
                    >
                      Try again
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* dev-only: simulate a failure without waiting */}
            {view === "loading" && (
              <div className="mt-4 text-right">
                <button
                  onClick={() => setView("error")}
                  className="text-[10px] uppercase tracking-wide"
                  style={{ fontFamily: "'Inter', sans-serif", color: "rgba(36,31,46,0.35)" }}
                >
                  Preview: simulate failure
                </button>
              </div>
            )}
          </>
        )}

        {/* ---------------- GRADED ---------------- */}
        {view === "graded" && session && (
          <>
            <SessionBar />

            <div className="mb-6 space-y-3">
              <p className="text-xs uppercase tracking-[0.15em] mb-1" style={{ fontFamily: "'Inter', sans-serif", color: COLORS.chromeTextMuted }}>
                Rubric key
              </p>
              {[
                { title: null, items: RUBRIC.filter((r) => r.id === "thesis") },
                { title: "Body ¶1", items: RUBRIC.filter((r) => r.group === "Body ¶1") },
                { title: "Body ¶2", items: RUBRIC.filter((r) => r.group === "Body ¶2") },
                { title: null, items: RUBRIC.filter((r) => r.id === "conclusion") },
              ].map((section, si) => (
                <div key={si}>
                  {section.title && (
                    <p className="text-[10px] uppercase tracking-wide mb-1" style={{ fontFamily: "'Inter', sans-serif", color: "rgba(74,63,92,0.55)" }}>
                      {section.title}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    {section.items.map((r) => {
                      const missing = isMissingDisplay(r.id);
                      const s = effScore(r.id);
                      const t = missing ? TIER.missing : tierFor(s);
                      const isActive = active === r.id;
                      const overridden = overrides[r.id] !== undefined;
                      return (
                        <button
                          key={r.id}
                          onClick={() => {
                            setActive(r.id);
                            const el = document.getElementById(`para-${r.id}`);
                            if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
                          }}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded text-xs transition-all"
                          style={{
                            fontFamily: "'Inter', sans-serif",
                            fontWeight: 600,
                            background: isActive ? COLORS.card : "rgba(63,53,80,0.06)",
                            color: isActive ? COLORS.cream : COLORS.chromeTextMuted,
                          }}
                        >
                          {r.label}
                          <span
                            className="w-4 h-4 rounded-full flex items-center justify-center text-[10px]"
                            style={{ background: t.bg, color: t.text, boxShadow: overridden ? "0 0 0 2px white" : "none" }}
                          >
                            {missing ? "!" : s}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-8">
              <div className="relative rounded px-10 py-12 shadow-sm" style={{ background: COLORS.paper, color: COLORS.ink }}>
                <div className="absolute -top-4 -right-3 px-3 py-1.5 rounded rotate-[-6deg] select-none" style={{ background: COLORS.card, color: COLORS.cream }}>
                  <span style={{ fontFamily: "'Caveat', cursive", fontWeight: 700, fontSize: "1.4rem" }}>{overall}</span>
                  <span className="text-[10px] ml-1 tracking-wide" style={{ fontFamily: "'Inter', sans-serif", opacity: 0.75 }}>
                    / 4 avg
                  </span>
                </div>

                <p className="text-xs uppercase tracking-[0.15em] mb-2" style={{ fontFamily: "'Inter', sans-serif", color: COLORS.muted }}>
                  {studentName || "Student"} · {session.classId}
                </p>
                <h1 className="mb-8 pr-20" style={{ fontFamily: "'Fraunces', serif", fontSize: "2rem", fontWeight: 600, lineHeight: 1.15 }}>
                  {ESSAY.title}
                </h1>

                <div style={{ fontFamily: "'Fraunces', serif", fontSize: "1.0625rem", lineHeight: 1.85 }}>
                  {ESSAY.paras.map((para, i) => (
                    <p key={i} className="mb-5">
                      {para.map((chunk) => {
                        const isActiveChunk = active === chunk.id;
                        const rubricItem = RUBRIC.find((r) => r.id === chunk.id);

                        if (chunk.missing) {
                          return (
                            <span key={chunk.id} id={`para-${chunk.id}`} className="inline-flex items-center mr-1">
                              <button
                                onClick={() => {
                                  setActive(chunk.id);
                                  const el = document.getElementById(`note-${chunk.id}`);
                                  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
                                }}
                                className="px-2 py-1 rounded text-[11px] uppercase tracking-wide font-semibold"
                                style={{
                                  fontFamily: "'Inter', sans-serif",
                                  background: "transparent",
                                  border: `1.5px dashed ${TIER.missing.bg}`,
                                  color: TIER.missing.bg,
                                }}
                              >
                                ! {rubricItem.label} missing
                              </button>
                            </span>
                          );
                        }

                        const t = tierFor(effScore(rubricItem.id));
                        return (
                          <span key={chunk.id} id={`para-${chunk.id}`}>
                            <button
                              onClick={() => {
                                setActive(chunk.id);
                                const el = document.getElementById(`note-${chunk.id}`);
                                if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
                              }}
                              className="align-super mr-1 px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wide"
                              style={{
                                fontFamily: "'Inter', sans-serif",
                                fontWeight: 700,
                                background: isActiveChunk ? COLORS.card : t.bg,
                                color: isActiveChunk ? COLORS.cream : t.text,
                              }}
                            >
                              {rubricItem.label}
                            </button>
                            <span style={{ background: isActiveChunk ? "rgba(63,53,80,0.08)" : "transparent", borderRadius: 3 }}>
                              {chunk.text}
                            </span>
                          </span>
                        );
                      })}
                    </p>
                  ))}
                </div>
              </div>

              {/* Margin: every criterion, in order, fully annotated */}
              <div className="space-y-4">
                {RUBRIC.map((r) => {
                  const isOverriddenR = overrides[r.id] !== undefined;
                  const dispute = disputes[r.id] || { open: false, messages: [], pick: null, resolved: false };
                  const isActiveR = active === r.id;
                  const missingR = isMissingDisplay(r.id);
                  const t = missingR ? TIER.missing : tierFor(effScore(r.id));
                  return (
                    <div
                      key={r.id}
                      id={`note-${r.id}`}
                      className="rounded px-5 py-5"
                      style={{
                        background: COLORS.card,
                        boxShadow: isActiveR ? "0 0 0 2px rgba(255,255,255,0.4)" : missingR ? `0 0 0 1.5px ${TIER.missing.bg}` : "none",
                      }}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs uppercase tracking-wide" style={{ fontFamily: "'Inter', sans-serif", color: "#C9BFDA" }}>
                          {r.group ? `${r.group} · ` : ""}
                          {r.label}
                        </span>
                        <span
                          className="px-2 py-0.5 rounded text-xs font-semibold flex-shrink-0"
                          style={{ background: t.bg, color: t.text, fontFamily: "'Inter', sans-serif" }}
                        >
                          {missingR ? "! Missing" : `${effScore(r.id)} / 4 · ${t.label}`}
                        </span>
                      </div>
                      {isOverriddenR && (
                        <p className="text-[11px] mb-3" style={{ fontFamily: "'Inter', sans-serif", color: "#9C8FB3" }}>
                          {r.missing
                            ? `Flagged as missing by Claude — scored ${overrides[r.id]}/4 by you`
                            : `Originally ${r.score}/4 by Claude — corrected to ${overrides[r.id]}/4 by you`}
                        </p>
                      )}
                      {!isOverriddenR && <div className="mb-3" />}

                      <p className="text-[10px] uppercase tracking-wide mb-2" style={{ fontFamily: "'Inter', sans-serif", color: "#9C8FB3" }}>
                        What they did well
                      </p>
                      {missingR && r.strengths.length === 0 ? (
                        <p className="text-sm italic mb-5" style={{ fontFamily: "'Inter', sans-serif", color: "rgba(243,239,232,0.55)" }}>
                          Nothing to point to yet — no reasoning sentence is present.
                        </p>
                      ) : (
                        <ul className="space-y-2.5 mb-5">
                          {r.strengths.map((s, i) => (
                            <li key={i} className="flex gap-2.5" style={{ fontFamily: "'Inter', sans-serif", color: COLORS.cream, fontSize: "0.9375rem", lineHeight: 1.5 }}>
                              <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-2" style={{ background: COLORS.strengthDot }} />
                              <span>{s}</span>
                            </li>
                          ))}
                        </ul>
                      )}

                      <p className="text-[10px] uppercase tracking-wide mb-2" style={{ fontFamily: "'Inter', sans-serif", color: "#9C8FB3" }}>
                        {missingR ? "What's missing" : "What would strengthen it"}
                      </p>
                      <ul className="space-y-2.5 mb-4">
                        {r.critiques.map((c, i) => (
                          <li key={i} className="flex gap-2.5" style={{ fontFamily: "'Inter', sans-serif", color: COLORS.cream, fontSize: "0.9375rem", lineHeight: 1.5 }}>
                            <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-2" style={{ background: missingR ? TIER.missing.bg : COLORS.growthDot }} />
                            <span>{c}</span>
                          </li>
                        ))}
                      </ul>

                      <button
                        onClick={() => toggleReasoning(r.id)}
                        className="text-xs w-full text-left pt-3 flex items-center gap-1.5"
                        style={{ fontFamily: "'Inter', sans-serif", color: "#9C8FB3", borderTop: "1px solid rgba(255,255,255,0.12)" }}
                      >
                        <span style={{ transform: expandedReasoning.has(r.id) ? "rotate(90deg)" : "none", display: "inline-block", transition: "transform 0.15s" }}>▸</span>
                        {expandedReasoning.has(r.id) ? "Hide model's reasoning" : "Show model's reasoning"}
                      </button>
                      {expandedReasoning.has(r.id) && (
                        <p className="mt-2 text-xs italic" style={{ fontFamily: "'Inter', sans-serif", color: "rgba(243,239,232,0.7)", lineHeight: 1.6 }}>
                          {r.reasoning}
                        </p>
                      )}

                      <div className="mt-4 pt-4" style={{ borderTop: "1px solid rgba(255,255,255,0.12)" }}>
                        {!dispute.open && (
                          <button
                            onClick={() => openDispute(r.id)}
                            className="text-xs w-full py-2 rounded font-semibold"
                            style={{ fontFamily: "'Inter', sans-serif", background: "rgba(255,255,255,0.08)", color: COLORS.cream }}
                          >
                            Disagree with this score?
                          </button>
                        )}

                        {dispute.open && (
                          <div>
                            <p className="text-[10px] uppercase tracking-wide mb-3" style={{ fontFamily: "'Inter', sans-serif", color: "#9C8FB3" }}>
                              Discuss this grade
                            </p>

                            <div className="space-y-2.5 mb-3">
                              {dispute.messages.map((m, i) => (
                                <div key={i} className={m.role === "teacher" ? "flex justify-end" : "flex justify-start"}>
                                  <div
                                    className="rounded px-3 py-2 max-w-[85%] text-sm"
                                    style={{
                                      fontFamily: "'Inter', sans-serif",
                                      lineHeight: 1.5,
                                      background: m.role === "teacher" ? COLORS.cream : "rgba(255,255,255,0.08)",
                                      color: m.role === "teacher" ? COLORS.ink : COLORS.cream,
                                    }}
                                  >
                                    {m.text}
                                  </div>
                                </div>
                              ))}
                              {dispute.sending && (
                                <div className="flex justify-start">
                                  <div className="rounded px-3 py-2 text-sm" style={{ fontFamily: "'Inter', sans-serif", background: "rgba(255,255,255,0.08)", color: "rgba(243,239,232,0.6)" }}>
                                    Thinking…
                                  </div>
                                </div>
                              )}
                            </div>

                            {!dispute.resolved && (
                              <>
                                <div className="flex gap-2 mb-3">
                                  <input
                                    value={draftMap[r.id] || ""}
                                    onChange={(e) => setDraftMap((d) => ({ ...d, [r.id]: e.target.value }))}
                                    onKeyDown={(e) => e.key === "Enter" && sendMessage(r.id)}
                                    placeholder="What feels off about this score?"
                                    className="flex-1 px-3 py-2 rounded text-sm outline-none"
                                    style={{ fontFamily: "'Inter', sans-serif", background: "rgba(255,255,255,0.08)", color: COLORS.cream }}
                                  />
                                  <button
                                    onClick={() => sendMessage(r.id)}
                                    disabled={!(draftMap[r.id] || "").trim()}
                                    className="px-3 py-2 rounded text-xs font-semibold"
                                    style={{ fontFamily: "'Inter', sans-serif", background: COLORS.cream, color: COLORS.card, opacity: (draftMap[r.id] || "").trim() ? 1 : 0.4 }}
                                  >
                                    Send
                                  </button>
                                </div>

                                {dispute.pick != null && (
                                  <div className="rounded px-3 py-3" style={{ background: "rgba(255,255,255,0.06)" }}>
                                    <p className="text-[10px] uppercase tracking-wide mb-2" style={{ fontFamily: "'Inter', sans-serif", color: "#9C8FB3" }}>
                                      Finalize your score
                                    </p>
                                    <div className="flex gap-2 mb-3">
                                      {[1, 2, 3, 4].map((n) => (
                                        <button
                                          key={n}
                                          onClick={() => setDisputes((d) => ({ ...d, [r.id]: { ...d[r.id], pick: n } }))}
                                          className="w-9 h-9 rounded-full text-sm font-semibold"
                                          style={{
                                            fontFamily: "'Inter', sans-serif",
                                            background: dispute.pick === n ? COLORS.cream : "rgba(255,255,255,0.10)",
                                            color: dispute.pick === n ? COLORS.card : COLORS.cream,
                                            boxShadow: dispute.pick === n ? `0 0 0 2px ${tierFor(n).bg}` : "none",
                                          }}
                                        >
                                          {n}
                                        </button>
                                      ))}
                                    </div>
                                    <div className="flex gap-2">
                                      <button onClick={() => saveCorrection(r.id)} className="flex-1 text-xs py-2 rounded font-semibold" style={{ fontFamily: "'Inter', sans-serif", background: COLORS.cream, color: COLORS.card }}>
                                        Save correction
                                      </button>
                                      <button onClick={() => keepOriginal(r.id)} className="text-xs px-3 py-2 rounded font-semibold" style={{ fontFamily: "'Inter', sans-serif", background: "transparent", color: "#9C8FB3" }}>
                                        Keep original
                                      </button>
                                    </div>
                                  </div>
                                )}
                              </>
                            )}

                            {dispute.resolved && (
                              <p className="text-xs" style={{ fontFamily: "'Inter', sans-serif", color: "#9C8FB3" }}>
                                {isOverriddenR ? `Resolved — score corrected to ${overrides[r.id]}/4.` : "Resolved — original score kept."}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Finish grading */}
            <div className="mt-8 rounded px-6 py-5 flex items-center justify-between gap-4 flex-wrap" style={{ background: COLORS.card }}>
              {!finished ? (
                <>
                  <div>
                    <p style={{ fontFamily: "'Inter', sans-serif", color: COLORS.cream, fontSize: "0.9375rem", fontWeight: 600 }}>
                      Ready to finish grading this essay?
                    </p>
                    <p className="text-xs mt-1" style={{ fontFamily: "'Inter', sans-serif", color: "#9C8FB3" }}>
                      {correctedCount > 0
                        ? `${correctedCount} ${correctedCount > 1 ? "criteria" : "criterion"} corrected · ${acceptedAsIsCount} accepted as graded.`
                        : `All ${RUBRIC.length} criteria accepted as graded — no corrections made.`}
                      {openUnresolvedCount > 0 && (
                        <span style={{ color: "#E3B7AB" }}> You have {openUnresolvedCount} open discussion{openUnresolvedCount > 1 ? "s" : ""} to resolve first.</span>
                      )}
                      {openUnresolvedCount === 0 && unaddressedMissingCount > 0 && (
                        <span style={{ color: "#E3B7AB" }}> {unaddressedMissingCount} {unaddressedMissingCount > 1 ? "criteria" : "criterion"} still flagged as missing — you can finish anyway, or discuss it first.</span>
                      )}
                    </p>
                  </div>
                  <button
                    onClick={finishGrading}
                    disabled={openUnresolvedCount > 0}
                    className="px-5 py-2.5 rounded text-sm font-semibold uppercase tracking-wide"
                    style={{
                      fontFamily: "'Inter', sans-serif",
                      background: COLORS.cream,
                      color: COLORS.card,
                      opacity: openUnresolvedCount > 0 ? 0.4 : 1,
                      cursor: openUnresolvedCount > 0 ? "not-allowed" : "pointer",
                    }}
                  >
                    Finish grading
                  </button>
                </>
              ) : (
                <div className="flex items-center justify-between w-full flex-wrap gap-3">
                  <p style={{ fontFamily: "'Inter', sans-serif", color: COLORS.cream, fontSize: "0.9375rem" }}>
                    <span style={{ color: COLORS.strengthDot, fontWeight: 700 }}>✓</span> Grades saved for {studentName || "this student"} — {finishedAt}.
                  </p>
                  <button
                    onClick={nextEssay}
                    className="text-xs px-4 py-2 rounded font-semibold uppercase tracking-wide"
                    style={{ fontFamily: "'Inter', sans-serif", background: COLORS.cream, color: COLORS.card }}
                  >
                    Next essay →
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {showBackToTop && (
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="fixed bottom-6 right-6 rounded-full px-4 py-3 flex items-center gap-2 shadow-lg"
          style={{ fontFamily: "'Inter', sans-serif", fontWeight: 600, fontSize: "0.8125rem", background: COLORS.card, color: COLORS.cream, zIndex: 50 }}
        >
          <span style={{ fontSize: "0.9rem" }}>↑</span> Back to top
        </button>
      )}
    </div>
  );
}
