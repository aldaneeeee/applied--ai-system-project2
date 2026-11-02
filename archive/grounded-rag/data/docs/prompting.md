# Prompting Techniques

A prompt is the input given to a language model. How a prompt is written has a
large effect on the quality of the model's output.

## System prompts

A system prompt sets the model's role, rules, and constraints for the whole
conversation. In a RAG system, the system prompt is where you instruct the model
to answer only from the provided context and to cite its sources.

## Zero-shot and few-shot prompting

Zero-shot prompting asks the model to perform a task with no examples. Few-shot
prompting includes a small number of worked examples in the prompt to show the
model the desired format and behaviour. Few-shot prompting often improves
accuracy on tasks with a specific output format.

## Chain-of-thought prompting

Chain-of-thought prompting asks the model to reason step by step before giving a
final answer. Working through intermediate steps tends to improve performance on
tasks that require multi-step reasoning, such as math or logic problems.

## Structured outputs

Structured outputs constrain the model to return data in a fixed shape, such as
JSON that matches a schema. This makes the output easy to parse and validate,
which is important when the model's response feeds into other software rather
than being read directly by a person.
