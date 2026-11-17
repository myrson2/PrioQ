# Mission — Smart Student Task Prioritization Queue System

## Executive Summary
A personal task queue for a student that answers one question: **"What should I work on right now?"** It ranks quizzes, homework, exams, and projects using deadline, grade weight, effort, and difficulty, and shows *why* each task ranks where it does. Built first for its owner; opened to a small group of testers after Milestone 2.

## Problem Statement & Friction
Deadline-only to-do lists treat a 1-hour, 5% quiz due tomorrow and a 20-hour, 30% project due in two weeks as "the quiz first, always", until the project becomes an emergency. The result is decision fatigue, procrastination on high-impact work, and energy wasted on low-impact tasks.

## Target Persona & Workflow
- **Primary — the owner:** a student juggling several courses who wants a short, trustworthy "do this next" list instead of a long list sorted by date.
- **Secondary — usability testers:** a handful of fellow students, after M2, each with their own private account.
- **Workflow:** add a task in seconds (title, category, due date/time, grade weight, estimated hours, difficulty) → open the queue → work the top item → mark tasks done → occasionally adjust daily study hours.

## Value Proposition
- **Starts big work early:** time pressure compares remaining effort with the study hours actually left, so large projects surface before they're emergencies.
- **Explainable:** every score shows its parts; nothing is a black box.
- **Grows smarter:** the rule-based score is the baseline an ML model must beat in M3.

## Success Metrics
| # | Metric | How it's checked | Milestone |
|---|---|---|---|
| K-1 | I stop missing deadlines and start big projects earlier | Owner's own use over a few weeks | After M2 |
| K-2 | Testers add a task in < 30 s, and agree the top-3 list matches what they'd do next | Usability test sessions | M2 |
| K-3 | The ML model ranks tasks better than the rule-based formula on a held-out test set | Offline evaluation, metric fixed in M3 spec | M3 |
