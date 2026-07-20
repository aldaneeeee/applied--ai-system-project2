# Guardrails for AI Applications

Guardrails are the checks and constraints that keep an AI application behaving
safely and predictably, especially when something goes wrong.

## Input validation

Input validation rejects or cleans user input before it reaches the model.
Examples include limiting the length of a question, stripping empty input, and
detecting obviously malformed requests. Validating input early prevents wasted
work and reduces the attack surface of the application.

## Retrieval thresholds

A retrieval threshold is a minimum similarity score below which retrieved
passages are considered too irrelevant to use. When the best passage falls below
the threshold, the system abstains instead of answering from weak context. This
is a key defence against confidently wrong answers.

## Self-verification

Self-verification is a step in which the system checks its own output before
returning it. In a RAG system, a verification step confirms that the generated
answer is grounded in the cited passages; if it is not, the system can retry the
retrieval or abstain. Self-verification turns a single-shot generator into an
agentic workflow that plans, acts, and checks its own work.

## Graceful failure

Graceful failure means that when the system cannot complete a request, it fails
in a safe and understandable way: it returns a clear message, logs the problem,
and never crashes or returns a misleading answer. Falling back to a safe default
is preferable to producing an unreliable result.
