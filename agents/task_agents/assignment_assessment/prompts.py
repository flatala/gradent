"""Prompts for the assignment assessment workflow."""

SYSTEM_PROMPT = """You are an expert academic assistant specializing in analyzing course assignments.

Your role is to:
1. Carefully analyze assignment requirements and rubrics
2. Estimate realistic effort using PERT methodology (optimistic, most likely, pessimistic)
3. Assess difficulty based on required skills, complexity, and prerequisites
4. Break down work into actionable milestones
5. Identify prerequisite knowledge needed
6. Flag potential risks and dependencies

Be realistic and err on the side of slightly overestimating effort.
Consider that students often underestimate debugging, testing, and documentation time.
"""

ANALYSIS_PROMPT = """Analyze this assignment and provide a detailed assessment:

Assignment Title: {title}
Course: {course_name}
Due Date: {due_date}

Description:
{description}

Provide your analysis considering:
1. What are the main deliverables?
2. What prerequisite knowledge/skills are required?
3. What are the major milestones/phases of work?
4. What could be challenging or time-consuming?
5. Are there any external dependencies or blockers?
6. How much time would a typical student need?

Think through this step by step before generating the structured assessment."""

STRUCTURED_OUTPUT_PROMPT = """Based on your analysis, generate a structured assessment in JSON format.

The assessment should include:
1. Effort estimates (low, most likely, high) in hours
2. Difficulty rating (1-5 scale)
3. Risk score (0-100, considering complexity, time pressure, dependencies)
4. Confidence in your assessment (0-1)
5. Detailed milestones with estimated hours and timing
6. Prerequisite topics
7. Deliverables list
8. Any blocking dependencies
9. A brief summary

Return valid JSON matching this schema:
{{
  "effort_hours_low": <float>,
  "effort_hours_most": <float>,
  "effort_hours_high": <float>,
  "difficulty_1to5": <float>,
  "weight_in_course": <float or null>,
  "risk_score_0to100": <float>,
  "confidence_0to1": <float>,
  "milestones": [
    {{"label": "string", "hours": <float>, "days_before_due": <int>}}
  ],
  "prereq_topics": ["string", ...],
  "deliverables": ["string", ...],
  "blocking_dependencies": ["string", ...],
  "summary": "string"
}}

Ensure valid JSON with no additional text or markdown formatting."""
