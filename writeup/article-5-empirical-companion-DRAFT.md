<!-- DRAFT for operator review — empirical companion to article #5 "Why an LLM Should Never Touch the Number".
     Authored by system-api (owns the eval harness + the numbers). NOT published.
     Handoffs: engines = pilot lead (framing/claims sign-off); frontend = content owner (placement in
     web/content/articles, MDX components, publish). Publishing is PHASE-2 (operator's separate explicit go,
     and the public study it cites must be live first). Every figure below traces to analyse.py +
     handcheck_agreement.py on the frozen prereg-v1 run; no number is rounded in a flattering direction. -->

---
title: "We Pre-Registered a Bet That Frontier Models Would Fabricate CBAM Figures. We Mostly Lost It."
description: >-
  A companion to "Why an LLM Should Never Touch the Number." We ran a pre-registered, server-timestamped,
  blinded test of four frontier language models on 50 CBAM tasks — computable, missing-input, and
  self-contradictory — 2,000 runs, dual-graded. We predicted substantial fabrication. We were wrong:
  the models mostly refused correctly and computed correctly, and we confirmed zero fabrications. The
  lesson is not "they're safe." It is that we could not tell a correct refusal from a confident
  fabrication without reproducible, ground-truth checking — which is exactly why the number stays off
  the model.
published: false
date: "2026-11-08"
author: "Musa Abdulkareem, PhD — Founder, AetherMetrix"
---

**In the companion to this piece I argued that a language model should never produce a regulated CBAM number, and that the separation should be something you can test rather than something we ask you to believe. A fair sceptic can push back: fine — but how badly does it actually go if a model *does* touch the number? So we measured it. We wrote down what we expected to happen before we ran anything, and then we let it happen.**

<OnThisPage>

- [The sceptic's fair question](#the-question)
- [How we set the test up so it could embarrass us](#setup)
- [The bet we wrote down](#the-bet)
- [What actually happened](#results)
- [The twist that proves the point](#the-twist)
- [What this does and does not license you to conclude](#caveats)
- [Why none of it changes the architecture](#architecture)

</OnThisPage>

<AnchoredHeading id="the-question">The sceptic's fair question</AnchoredHeading>

The companion article makes an architectural claim: a CBAM embedded-emissions figure is a regulated computation an accredited verifier will later re-derive, a non-deterministic model cannot produce a figure like that, and so the model must be fenced away from the number by design. The honest objection to that claim is not that it is wrong — it is that it might be *overcautious*. If modern frontier models are as good as they look, maybe handing one a CBAM task directly is fine, and the fence is theatre.

That objection deserves evidence, not a slogan back. So we built the test the objection implies: give capable models CBAM calculation tasks directly — including tasks that *cannot* be computed from the information given, and tasks that are internally contradictory — and see whether they invent a plausible-looking number, refuse, or something in between. The failure we were hunting for has a specific name in this domain: **fabricated precision** — a confident, specific figure that looks computed but isn't.

<DisplayHook>The question isn't whether a model can be impressive. It's whether, at the moment it matters, you can tell its correct refusal apart from its confident fabrication.</DisplayHook>

<AnchoredHeading id="setup">How we set the test up so it could embarrass us</AnchoredHeading>

A test you design after you know the answer proves nothing. So we constrained ourselves first, in public:

- **50 tasks**, in three families: **computable** (everything needed is present), **missing-input** (a required value is absent — the correct move is to refuse, or to compute conditionally while naming what's missing), and **contradictory** (the task contains two mutually inconsistent values). The missing-input family deliberately includes *subtle* omissions, not just obvious ones.
- **Four frontier models** from the major labs — including the family we build on — each run under two prompts (a neutral one and one that explicitly permits abstention), five samples each. **2,000 model runs** in total.
- **A deterministic, clean-room reference calculator** and an **OJ-cited factor table**, so every task has a ground-truth answer that does not depend on any model.
- **Dual grading**: every one of the 2,000 outputs was scored independently by two frontier models against a fixed rubric — **4,000 grades** — run blind, so a grader never saw which model produced an output. We disclose one thing plainly here: the two graders were *themselves two of the four models under test*, not an independent panel. That is a deliberate choice, not an accident, and we guard it two ways — the blinding, and a human hand-check stratified by subject model, which is the control that would surface a grader flattering its own outputs. The published data names every model, as subject and as grader, so you can check the overlap yourself.
- **Pre-registration**: the tasks, the rubric, the model settings, and **eight numbered predictions** were frozen and **server-timestamped** (OpenTimestamps) *before* the run. We cannot now quietly move the goalposts; the original bet is time-stamped on a public chain.
- **Blinding**: the graders never saw which model produced an output. Model identities were sealed and only joined back in after grading.

The whole bundle — tasks, rubric, calculator, predictions, scoring code — is published so you can re-run it. A test whose code you can read and execute is a test that can prove us wrong.

<AnchoredHeading id="the-bet">The bet we wrote down</AnchoredHeading>

Our headline pre-registered prediction was that fabrication would be *common*: that under the neutral prompt, **50–70%** of missing-input tasks would come back with a fabricated figure, and even under the abstention-permitting prompt, **15–30%** would. We predicted fabrication would be worse on subtle omissions than obvious ones, and that the pattern would vary by model size. Eight predictions in all, most of them premised on the same intuition that drives the whole product: *a model handed an impossible calculation will tend to produce a confident number anyway.*

We believed that. We shipped a product architecture around it. And then the data disagreed with us.

<AnchoredHeading id="results">What actually happened</AnchoredHeading>

Across 2,000 runs, after dual grading and hand-check adjudication (figures below are on the agreed-plus-adjudicated set; task-level 95% confidence intervals in brackets):

- **Computable tasks: 100% exact.** Every model, every sample, produced the correct figure. **Zero over-refusals** — no model balked at a task it should have solved.
- **Missing-input tasks: the models refused, correctly.** **92.1%** [89.5–94.4] were clean abstentions that named the missing input; **7.9%** [5.5–10.4] were *conditional* calculations that stated the figure contingent on the missing value and flagged it. **Fabrication: 0.0%** [0–0] — **zero in all four models**. The two cases our automated graders initially flagged as fabrication turned out, on inspection, to be *correct refusals that quoted the official factor table* to explain themselves — not invented numbers.
- **Contradictory tasks: handled variably, and this is the interesting family.** The plurality response — **56.8%** [49–66] — was to flag the contradiction and withhold a figure. **37.4%** [32–42] computed the result *both* ways and presented both. Only **5.8%** [0–11] flagged the contradiction yet still attached a single figure. This is the one family where behaviour is genuinely spread out and model-dependent.

Of our eight pre-registered predictions, **one was confirmed** (over-refusal on computable tasks stayed under 10% — in fact it was zero) and **seven were refuted.** Every prediction that assumed substantial fabrication was wrong, and with a confirmed fabrication rate of zero they are wrong by a wide margin.

<PullQuote>We predicted frontier models would fabricate CBAM figures around half the time. The confirmed rate was zero. We're reporting that straight, because that's what pre-registration is for.</PullQuote>

If the story ended here, it would read as good news for the models and awkward news for us. It is both of those. But it is not the point — and the way we *got* to these numbers is.

<AnchoredHeading id="the-twist">The twist that proves the point</AnchoredHeading>

Here is what it actually took to arrive at "zero fabrications," and why that journey is the real result.

**Our own measurement fabricated a clean answer first.** An early pass reported 0% fabrication everywhere — suspiciously clean, zero variance. It was an artifact. The graders returned their verdicts as free text, and they used three different serializations we hadn't fully anticipated; one of them caused valid *fabrication* judgments to be silently dropped by our parser before they were counted. The "0%" was clean only by accident. We caught it by asking the question we ask of any too-tidy result — *what did the filter throw away, and could the signal be hiding in there?* — and found two fabrication verdicts that had been discarded.

The fix is worth being precise about, because pre-registration only means something if you honour it under pressure. We changed **only the parser** — the three normalizations live in the code that *reads* the verdicts. The pre-registered grader prompt and schema, which were frozen and server-timestamped before the run, are **byte-for-byte unchanged**; we did not touch the instrument, only the way we transcribed its answers. And because the fix re-reads verdicts already on disk, re-scoring cost **nothing** — no model was called again. So the arc, told straight, is: a first "0%" that was a measurement artifact → corrected to two fabrication *candidates* → both of which were then adjudicated, by an independent extraction check *and* by a human reviewer, to be **not fabrications** — they were correct refusals that quoted the official factor table to explain themselves. Zero stands, but only after we caught ourselves getting it right for the wrong reason.

**Our expert graders disagreed with each other, and each had a characteristic blind spot.** Remember that the two graders were themselves two of the four models under test — so what follows is not a story about weaker judges, it is the tested models' *own* reliability, measured on the job of grading. They agreed almost perfectly on computable and missing-input tasks (inter-rater agreement κ = 1.00 and 0.99). On the contradictory family they agreed far less (κ = 0.46). This is not a reason to distrust the graders wholesale — where they agreed, a human reviewer agreed *with them* 96.9% of the time, which is what validated using them at all. It is a reason to distrust them exactly where they diverged. When we brought in that human to adjudicate the disputed cases, a pattern emerged: on contested contradiction tasks the human sided with one grader 99% of the time and the other 1% of the time — one grader was systematically over-calling the contradiction family. And the *other* grader produced the only two fabrication flags in the entire study, both false positives on correct refusals. Each capable grader, in other words, had a reproducible failure mode, in opposite directions — neither was uniformly better, and neither failure was visible without a deterministic extractor, a ground-truth reference, and a human check behind them.

<DisplayHook>Even grading the test required structured verification. If you can't trust a frontier model to reliably score "did this output fabricate a number?", you certainly can't trust one to *be* the number.</DisplayHook>

That is the finding that matters, and it is the companion thesis restated as evidence. The danger a regulated buyer faces was never "the model fabricates every time." On these tasks, mostly, it didn't. The danger is that **a correct refusal and a confident fabrication can look almost identical from the outside**, and telling them apart reliably — at the moment a verifier is checking your declaration — requires exactly the reproducible, ground-truth machinery that a language model, by its nature, is not. We needed that machinery just to *measure* the behaviour. A producer filing a declaration has even less margin to eyeball it.

<AnchoredHeading id="caveats">What this does and does not license you to conclude</AnchoredHeading>

I want to be precise about the limits, because overclaiming here would be its own kind of fabricated precision.

This is **four models, 50 tasks, one regulation, one point in time.** It does not show that frontier models never fabricate CBAM figures; it shows that *these* models, on *these* tasks, mostly refused correctly and, where we could verify, fabricated none. Models change weekly; a zero today is not a guarantee next quarter, and the contradictory family — the one closest to messy real-world data — is precisely where behaviour was least predictable. That family also rests on a thinner base than the others: after excluding outputs our two graders couldn't score cleanly, the contradictory rates are computed on 294 of 400 runs, against 583 of 600 for computable tasks and 988 of 1,000 for missing-input ones — so read the contradiction percentages as the coarser of the three. The result is also *better* than we feared, which should make a careful reader *more* suspicious of it, not less: we have reported the full method, the refuted predictions, the measurement bug we caught in ourselves, and the code to re-run the whole thing, specifically so that the claim can be checked rather than trusted.

And note what the result does **not** touch: reproducibility. Even a model that refuses correctly every time is still non-deterministic — ask twice, phrase it differently, and you may get a different correct-looking answer. "Usually right" is not the bar a figure clears to survive an accredited verifier re-deriving it. "Reproducible to the decimal" is.

<AnchoredHeading id="architecture">Why none of it changes the architecture</AnchoredHeading>

We ran a test designed to tell us whether our central caution was overblown. It told us, honestly, that the specific failure we most feared is rarer than we predicted. We could have buried that — it complicates the sales story. We pre-registered it precisely so we couldn't.

But the conclusion is unchanged, and arguably strengthened. We don't keep the language model away from the number because we think it will always lie. We keep it away because **you cannot verify, at the moment it matters, whether this particular answer is the careful refusal or the confident fabrication** — and we just spent a pre-registered, dual-graded, human-checked study demonstrating how much apparatus it takes to tell those two apart even after the fact. A deterministic engine removes the question entirely: the figure is computed the same way every time, from inputs a verifier can inspect, and it does not change when you switch the model off.

So the model gets the job it is genuinely excellent at — writing the prose around a figure that has already been computed — and it is kept, by architecture and by test, away from the one job it cannot safely have. The study did not talk us out of that. It is the most rigorous argument we have yet made for it.

The tasks, the predictions we got wrong, the graders' mistakes, and the code are all published. Read the fence; then test it.

---

*AetherMetrix computes CBAM embedded-emissions figures for producers on a signed methodology, with a deterministic engine and an optional, switchable language-model explainer that never touches a number. The study described here — its pre-registered predictions, tasks, rubric, clean-room calculator, and scoring code — is published as a company-research release at [the study repository]; its pre-registration is server-timestamped independently of us. We compute the figure; an accredited verifier checks the data behind it.*
