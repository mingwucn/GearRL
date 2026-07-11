# CAE Refinement Audit v1

This audit extends the previously reported single-case refinement sequence to 32 by 48 mesh divisions. Peak von Mises stress does not approach a stable value: the last two relative changes are 12.6% and 14.0%, both above the declared 5% limit and increasing with refinement.

Consequently, `involute-tooth-root-plane-stress-v3` is retained only as an exploratory static screening model. `StaticStrengthAdmissionPolicy` prevents it from admitting or rejecting certificate-bearing candidates until a replacement model passes representative convergence, independent-reference, and classification-stability gates.
