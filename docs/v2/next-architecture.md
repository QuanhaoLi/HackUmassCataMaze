<!--
Created at: 2026-11-14 22:37 EST
Created by: Codex
Last Modified at: 2026-11-14 22:37 EST
Last Modified by: Codex
-->

# V2.2 architecture decision required

## Evidence

The V2.1 program established the engineering pipeline and isolated causal failures:

- three independent linear heads can create large action-distribution divergence;
- reward v3 and style constraints can force aggressive shooting and explorer first visits;
- preserving the V1 trunk protects aggregate effectiveness better than full fine-tuning;
- linear heads cannot simultaneously satisfy aggressive hits, cautious survival, explorer low-revisit and every hard-opponent effectiveness gate;
- more scalar reward or larger loss weights move failures between gates rather than solving all of them;
- no branch reached model-side release eligibility, so quantization and firmware work remain correctly blocked.

## Recommended option: V2.2 nonlinear persona adapters

Keep the frozen V1 sensory encoder and shared GRU, but insert one residual adapter per persona after the recurrent output:

```text
r_persona = r + W2_persona(SiLU(W1_persona(r)))
logits_persona = actor_persona(r_persona)
```

Recommended adapter width:64. Zero-initialize `W2` and copy V1 actor/critic heads so step-0 remains V1-equivalent. Train only adapters and heads under reward v3 and the already validated private transition constraints.

Estimated cost:

- approximately99k additional parameters across three adapters;
- total model around1.12M parameters;
- expected W8A16 artifact still below the1.8MB budget, subject to export measurement;
- no observation/action/hidden/firmware contract change;
- one resident model and three private hidden states remain unchanged.

Why this is the recommended expansion: the adapter can transform shared recurrent features nonlinearly for accuracy, survival and novelty while preserving the V1 memory and avoiding three complete models.

## Alternative option: revise persona acceptance semantics

The best V2.1 branches already produce visibly distinct policies and pass aggregate effectiveness, but fail some original proxy metrics. The product owner could redefine cautious style around ammo restraint rather than raw death rate, or explorer style around first-visit throughput without requiring lower revisit in a perfect maze.

This is a product-definition change, not an engineering shortcut. It requires an explicit replacement ADR and new frozen gates before any existing checkpoint can be reconsidered. The V2 model owner does not make this choice implicitly.

## Forbidden response

- do not package the closest failed checkpoint;
- do not lower gates only in the quantization or manifest layer;
- do not deploy any V2.1 branch;
- do not overwrite V1 artifacts;
- do not start V2.2 until the product owner selects architecture expansion or metric revision.
