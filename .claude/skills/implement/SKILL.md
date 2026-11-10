---
name: implement
description: Implement one approved phase from a PRD and plan using feedback loops.
argument-hint: "@prd/<feature>.md @plans/<feature>.md implement phase <N>"
disable-model-invocation: true
---

# Implement

## 1. Understand the Phase

Read the referenced PRD and plan. Explore the codebase to understand the relevant files,
patterns, and conventions. If the request does not identify a phase, ask which one.

Implement only that phase. Do not begin the next one.

## 2. Implement the Phase

Run /ttd and follow the skill's instructions. Be sure to implement any other remaining requirements using the project's normal process. 

## 3. Run Feedback Loops

Run test suite, formatter, linter and additional feedback loops as needed. 

## 4. Manual Verification

Answer the question "How do I verify this phase or feature manually in the browser?" After answering this question, stop and wait for the user to verify that manual verification has passed. Fix any problems user has before manual verification can be passed. 

## 5. Finish the Phase

1. Update PROMPTS.md using formatting found in PROMPTS.md. 
2. Commit the completed phase. 
3. Push the commit to github