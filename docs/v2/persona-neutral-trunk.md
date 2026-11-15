<!--
Created at: 2026-11-14 21:09 EST
Created by: Codex
Last Modified at: 2026-11-14 21:09 EST
Last Modified by: Codex
-->

# V2.1 persona-neutral shared trunk

## Transformation

Starting from the accepted recurrent checkpoint:

1. compute the mean of `scalar_encoder[0].weight[:,43:46]` across the three persona columns;
2. copy that mean back into all three columns;
3. zero `persona_gamma` and `persona_beta`;
4. freeze visual, scalar, fusion, GRU, gamma and beta parameters;
5. train only three actor and three critic heads.

For any fixed spatial/scalar features other than persona and any fixed hidden state, changing one-hot persona now leaves the recurrent feature identical. The selected actor head is the only source of behavior difference.

## Required tests

- the three scalar persona columns are bit-identical after transformation;
- gamma/beta are zero and non-trainable;
- shared trunk and hidden output are counterfactually identical across personas;
- actor/critic heads receive gradients;
- internal same-feature JS equals deployment counterfactual JS within `1e-6`;
- checkpoint metadata records variant `catamaze.model.persona-heads.v2.1`.

## Controlled run

- source recurrent checkpoint SHA: `d155f283f73754c9dbb9d7142f8221bde4a6de27dc8b8c1385f63137bf85c597`;
- reward: `catamaze.reward.persona.v3`;
- style coefficient: `0.02` with normalized constraints;
- curriculum: C;
- learning rate: `3e-5`;
- target:5M before evaluation;
- no extension unless both style and effectiveness improve.

## Deployment consequence

The exported actor graph may retain the three-value persona one-hot for schema compatibility, but the shared trunk treats all three values identically. C++ continues selecting the corresponding row of `logits_all[1,3,9]`. No firmware integration is authorized by this decision.
