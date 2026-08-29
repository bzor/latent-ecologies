# Scientific and technical voice

## Scope

This is the default editorial standard for the entire Bzor Computational Studio. It applies to Study and Seed titles, summaries, descriptions, Discord reports, review captions, overlay text, field notes, package copy, and public-site text.

KC may add visual or expressive treatment during Look Development and the detail pass. The system's language remains scientific and technical unless KC explicitly requests another register for a specific output.

## Default register

Describe the system as a computational model, implementation, experiment, or observed output. Prefer the vocabulary of the relevant field: dynamical systems, agent-based modelling, cellular automata, numerical integration, graph dynamics, field methods, rendering, or software engineering.

Use plain technical language. A reader should be able to identify:

- the question or mechanism under study;
- state variables, update rules, boundary conditions, and stochastic inputs;
- implementation and numerical method;
- parameters and units where applicable;
- measured or directly observed outcomes;
- limitations, uncertainty, and unresolved questions;
- provenance and reproduction requirements.

## AI-style exclusions

Display text must not contain em dashes. Use a period, colon, comma, parentheses,
or a short hyphen where grammar permits.

Avoid negative parallelism such as `it is not X, it is Y`, `not just X`, and
`not merely X`. State the technical claim directly.

Remove stock AI-style phrasing, including:

- chatbot framing such as `let's dive in`, `here is what you need to know`,
  `I hope this helps`, and offers to continue;
- inflated significance such as `serves as a testament`, `pivotal moment`,
  `showcases the power`, and claims about an `evolving landscape`;
- fake depth markers such as `at its core`, `fundamentally`, and `the real question`;
- promotional adjectives, vague importance claims, and generic positive conclusions;
- rhetorical questions that immediately answer themselves;
- forced metaphors, anthropomorphic narration, and decorative scientific vocabulary;
- repetitive rule-of-three lists, synonym cycling, false ranges, and dramatic fragments;
- filler, excessive hedging, signposting, and text that tells the reader how to react.

Prefer a direct sentence with a defined subject, operation, result, and evidence.
Vary sentence length only when it improves clarity. Do not add personality by weakening
technical precision.

The mechanical validator rejects high-confidence patterns in Seed display fields and
Study cards. It checks em dashes, negative parallel constructions, and a bounded list of
stock phrases. Mechanical checks do not replace a final editorial pass. Before a display
output is accepted, read it once for AI cadence, vague authority, inflated significance,
and formulaic structure, then rewrite any sentence that still sounds generated.

## Claim discipline

Every claim must be identifiable as one of:

- **measured:** computed from defined data by a stated method;
- **derived:** calculated from other recorded values;
- **observed:** visible in a specified run or artifact but not reduced to a metric;
- **hypothesized:** a proposed explanation that still requires a test;
- **referenced:** supported by a named paper, dataset, or other source.

Do not convert a visual resemblance into a scientific claim. Terms from biology, physics, ecology, neuroscience, or other disciplines require either a cited basis or an explicit statement that they are analogies. A model designed from scratch is a computational hypothesis, not evidence about the natural system it resembles.

For paper-based Studies, label each implementation as reproduction, interpretation, adaptation, or mutation. State material departures from the source method. Do not imply numerical or scientific equivalence without a validation result that supports it.

Metrics must include a definition or a path to one. Scores used for search, ranking, or diagnostics must not be described as scientific validation or as measures of quality unless that interpretation has been established.

## Titles

Titles should normally identify the mechanism, variable, method, or observed regime. Prefer:

- `Refractory trail reinforcement with saturation-dependent repulsion`
- `Nonlocal affinity graph with synchronous position updates`
- `Radius-2 field deposition under opposed rotational bias`

The one permitted exception is a Study's main display title. KC may deliberately select a
concise poetic title when it gives the work a useful identity. Pair it with a technical
subtitle that identifies the mechanism or method. The summary, description, labels,
parameters, claims, and limitations remain scientific and technical. A poetic title must
not imply that an analogy or scientific interpretation has been established.

Outside that KC-approved main-title slot, avoid poetic naming, implied agency, or
unsupported naturalization, such as `Agents Learning to Heal` or `An Alien Ecology Awakens`.

A short internal slug may remain compact. When the main display title is poetic, the technical subtitle carries the mechanism or method.

## Summaries and descriptions

Use this order when practical:

1. **Question:** what is being tested or implemented.
2. **Method:** model class, state, update rule, implementation, and relevant controls.
3. **Result:** measured and observed behavior from identified runs.
4. **Status:** selected, rejected, inconclusive, or awaiting validation.
5. **Limitations:** what the evidence does not establish.

Avoid promotional, interpretive, or aesthetic filler: `evocative`, `poetic`, `organic`, `beautiful`, `compelling`, `mysterious`, `otherworldly`, `alive`, `cinematic`, and similar terms do not explain the mechanism or evidence.

Presentation details may be stated technically when relevant: camera projection, focal length, color mapping, luminance range, material model, sampling, compositing, and output encoding. Do not present those choices as scientific findings.

## Hermes reporting

Hermes should:

- use exact artifact paths, versions, parameters, checksums, durations, and test results;
- separate implementation status from simulation results and from KC's presentation decisions;
- define specialized terms or cite the source that defines them;
- report negative, null, and inconclusive results directly;
- state uncertainty instead of filling gaps with plausible narrative;
- challenge unsupported terminology before it enters canonical records.

Hermes should not:

- anthropomorphize agents or fields unless agency is part of the implemented model;
- use scientific vocabulary as atmosphere;
- invent mechanisms to explain an image after the fact;
- call a result emergent without identifying the macroscopic pattern and the local rules from which it arises;
- use engagement, novelty, or visual impact as evidence of model validity.

## Relationship to visual production

Look Development and the detail pass can alter geometry representation, materials, lighting, camera, typography, and composition. Those are KC-owned presentation layers. They must not silently change the selected simulation semantics, source data, or scientific description.

Public material may be visually polished, but its title, summary, labels, and claims remain tied to the canonical Study record and verified evidence.
