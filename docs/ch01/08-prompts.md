# Prompt Pack — engineering-grade prompts that don't hallucinate

Our team drives LLM agents (Amicode/opencode over Bedrock: Sonnet 4.6, Kimi
K2.5, GLM-5, …) for control design. Model output that *sounds* right but
invents device limits, physics constants, or results is the failure mode
that costs hackathon hours. These prompts encode the discipline that kept
this repo clean. Copy them verbatim; edit the bracketed parts.

## The five rules (put these in EVERY system prompt)

```text
RULES — violating any of these is a failed response:
1. PROVENANCE. Never state a numerical value (device limit, physical
   constant, fidelity, duration) unless it came from (a) code you ran in
   this session, (b) a file you read, or (c) the user's message. Cite the
   source next to the number. If you don't have it: say "unknown — here is
   the command to get it" and stop.
2. DEVICE TRUTH. Hardware limits come from the live Device object
   (pulser.AnalogDevice, or Device.from_abstract_repr of the cloud spec) at
   call time — never from memory, slides, or training data. Any script you
   write must read limits at runtime.
3. VERIFY BEFORE CLAIM. "It works" requires the executed command and its
   output in your response. A fidelity requires the scorer's printed output.
   An optimizer gradient requires a finite-difference check before first use.
4. ONE SCORER. All fidelities go through ch01/score.py (bell_fidelity).
   Never report a number from a different simulator, a model's internal
   estimate, or arithmetic-by-eye.
5. DECLARE ASSUMPTIONS. Anything assumed (noise rates, SPAM errors,
   tolerances) is listed under an "ASSUMED:" header so a scientist can
   strike it. No silent defaults.
```

## Task prompt: design/optimize a pulse

```text
Task: optimize [Omega(t), delta(t)] to prepare [target state] at
spacing r = [X] um on [device].

Method requirements:
- Read C6, max_amp, max_abs_detuning, clock_period, max_sequence_duration
  from the device object; print them first; abort if any read fails.
- Constrain Omega >= 0 everywhere (Pulser has no signed amplitude; a sign
  flip is a pi phase jump the channel cannot play).
- All durations in multiples of the device clock BEFORE scoring, so the
  reported fidelity is the fidelity of the flown artifact.
- After optimizing: re-roll the final waveform through score.bell_fidelity
  (independent of your optimizer's internal fidelity) and report BOTH
  numbers; they must agree to < 1e-4 or you investigate before reporting.
- Run the with_modulation=True check; report both fidelities.
Deliverables: the script, its full printed output, the pulse.toml, and a
table: {parameters, F_optimizer, F_rerollout, F_modulated, max slew}.
```

## Task prompt: review a claim / debug a discrepancy

```text
Claim under review: "[paste claim]".
1. Restate the claim as a testable prediction with a number and tolerance.
2. Write and RUN the minimal script that tests it. Show output.
3. Verdict: CONFIRMED / REFUTED / UNTESTABLE-BECAUSE-[reason]. No hedging.
4. If refuted, the incorrect step in the original reasoning, quoted exactly.
Rules 1-5 apply. If you cannot run code, respond only with the test plan —
do not guess the verdict.
```

## Task prompt: literature grounding

```text
Question: [physics/method question].
- Separate ESTABLISHED (textbook/paper you can name with arXiv id) from
  DERIVED-HERE (show the derivation) from ASSUMED (flag it).
- Do not attribute specific numbers to papers unless you can quote the
  paper's abstract or a file in this repo containing the excerpt. If
  uncertain about a citation's content, say "verify against the PDF" —
  never synthesize a plausible-sounding result.
```

## Review checklist (run on every agent PR/output before merging)

- [ ] Every number has a source (script output, file, or user input)?
- [ ] Device limits read at runtime, not hardcoded? (`grep -n "12.56\|125.6\|865723" — hits must read from Device`)
- [ ] Fidelities from the one scorer, post-quantization?
- [ ] Gradient/optimizer sanity check shown (FD comparison, selftest)?
- [ ] Assumptions section present?
- [ ] Units stated on every quantity (rad/µs vs MHz vs rad/ns bites — our
      teammate's Julia uses rad/ns; ours uses rad/µs)?
- [ ] Claims of "works on hardware" backed by a batch ID?

## Why these rules exist (incidents from this very project)

| Incident | Rule that catches it |
|---|---|
| Bundled template hardcoded C₆ = 862 690 (real: 865 723.02) and Ω bounds 8× over the envelope | 2 |
| Slide-deck envelope differs from the live FRESNEL spec (11.31 vs 12.57 rad/µs; layout min-filling rule undocumented) | 2, 3 |
| Optimizers drift into Ω < 0, unfly-able but great-scoring | task template |
| Noiseless emulator ranked our pulses in the *wrong order* vs the noise model | 5 (declare noise assumptions, re-rank) |
| Basis-ordering ('r','g' vs 'g','r') silently flips which index is \|rr⟩ | 3 (selftest before trusting) |
