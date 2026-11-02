# Evaluating AI Systems

Evaluation is how you turn "the system seems to work" into a measurable claim.
For a question-answering system, evaluation runs the system over a set of
questions with known expectations and scores the results.

## Groundedness

Groundedness, also called faithfulness, measures whether every claim in an
answer is supported by the source passages the answer was based on. An answer
that introduces facts not present in the sources is not grounded, even if those
facts happen to be true.

## Precision and recall

Precision is the fraction of returned results that are correct. Recall is the
fraction of the correct results that were returned. There is often a trade-off
between the two: returning more results tends to raise recall but lower
precision.

## Abstention accuracy

Abstention accuracy measures whether a system answers questions it should answer
and declines questions it cannot answer from its sources. A system that answers
everything, including questions outside its knowledge, has poor abstention
behaviour even if its answers to in-scope questions are good.

## Gold sets

A gold set is a curated collection of questions paired with expected answers or
answer criteria. Running a system against a gold set produces repeatable metrics
that can be tracked over time to detect regressions.
