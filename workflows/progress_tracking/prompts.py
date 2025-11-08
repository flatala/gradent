"""Prompts for progress tracking workflow."""

PARSE_USER_INPUT_PROMPT = """You are helping a student log their study progress. 
Extract structured information from their natural language input.

Current conversation context:
{context}

User just said: "{user_input}"

Extract the following if mentioned (return null if not found):
1. **assignment_reference**: Any mention of which assignment (name, number, keywords like "RL", "ML", "the project")
2. **duration**: How long they studied
   - Look for explicit times: "90 minutes", "1.5 hours", "2h 30m"
   - Look for vague terms: "a while", "briefly", "long session", "quick"
   - If vague, note it as estimate_only: true
3. **focus_level**: How focused they were (1-5 scale)
   - Keywords: "very focused/concentrated/deep work" → 4-5
   - Keywords: "somewhat focused/okay" → 3
   - Keywords: "distracted/interrupted/unfocused" → 1-2
4. **quality_level**: How productive they were (1-5 scale)
   - Keywords: "finished/completed/made progress/breakthrough/productive" → 4-5
   - Keywords: "okay/some progress" → 3
   - Keywords: "stuck/confused/didn't get much/wasted time" → 1-2
5. **notes**: Any additional context they provided
6. **intent**: Is this a progress update? Or something else like asking a question?

Respond in JSON format:
{{
    "intent": "log_progress" | "question" | "other",
    "assignment_reference": "string or null",
    "duration": {{
        "minutes": number or null,
        "is_estimate": boolean,
        "original_text": "what they said"
    }},
    "focus_level": number (1-5) or null,
    "quality_level": number (1-5) or null,
    "notes": "string",
    "confidence": "high" | "medium" | "low"
}}

Examples:
- "I worked on the RL assignment for 90 minutes and was really focused"
  → {{"intent": "log_progress", "assignment_reference": "RL assignment", "duration": {{"minutes": 90, "is_estimate": false}}, "focus_level": 5, "quality_level": null}}

- "Studied for a while, got distracted"
  → {{"intent": "log_progress", "assignment_reference": null, "duration": {{"minutes": 60, "is_estimate": true, "original_text": "a while"}}, "focus_level": 2, "quality_level": null}}

- "Just finished assignment 2, took 2 hours"
  → {{"intent": "log_progress", "assignment_reference": "assignment 2", "duration": {{"minutes": 120, "is_estimate": false}}, "focus_level": null, "quality_level": 5}}
"""


IDENTIFY_ASSIGNMENT_PROMPT = """You are helping identify which assignment the user is referring to.

User said: "{assignment_reference}"

Available assignments for this user:
{assignments_list}

Your task:
1. Match the user's reference to one of the available assignments
2. Consider: exact name matches, partial matches, keywords, assignment numbers
3. If multiple assignments could match, return all candidates with confidence scores
4. If no clear match, return empty list

Respond in JSON format:
{{
    "matches": [
        {{
            "assignment_id": number,
            "assignment_name": "string",
            "confidence": number (0.0-1.0),
            "reason": "why this matches"
        }}
    ],
    "needs_clarification": boolean
}}

Examples:
- User: "RL assignment" → might match "Reinforcement Learning Project" (high confidence)
- User: "assignment 2" → if there's "Assignment 2: ..." (high confidence)
- User: "the project" → if only one assignment with "project" (medium confidence)
- User: "the thing" → needs clarification (multiple possibilities)
"""


ASK_FOR_MISSING_INFO_PROMPT = """You are helping a student log study progress. Generate a natural follow-up question.

Current state:
- We have: {have_fields}
- We need: {missing_fields}
- Context: {context}

Generate ONE natural follow-up question to get the next missing piece of information.

Priority order:
1. assignment (critical - can't log without this)
2. duration (critical - can't log without this)
3. focus_rating (can assume 3 if user doesn't want to specify)
4. quality_rating (can assume 3 if user doesn't want to specify)

Guidelines:
- Be conversational and friendly
- Don't ask for everything at once
- If asking about assignment and we have candidates, list them
- If asking about duration and they said something vague, acknowledge it: "You mentioned 'a while' - about how many minutes would you estimate?"
- For focus/quality, explain the scale briefly: "On a scale of 1-5, how focused were you? (1=very distracted, 5=deep focus)"
- If we only need focus/quality and they seem reluctant, offer to assume neutral (3)

Examples:
- Missing assignment: "Which assignment did you work on?"
- Missing assignment with candidates: "I found a few assignments that might match. Did you work on: 1) Reinforcement Learning Project, or 2) Assignment 2: ML Basics?"
- Missing duration: "About how long did you study for?"
- Missing duration (had vague input): "You mentioned you studied 'a while' - roughly how many minutes would that be?"
- Missing focus: "How focused were you during this session? (1=very distracted, 5=deep focus)"
"""


CONFIRM_AND_LOG_PROMPT = """You are helping a student log their study progress. 

We've collected all the information:
- Assignment: {assignment_name}
- Duration: {minutes} minutes ({hours} hours)
- Focus level: {focus_rating}/5
- Quality level: {quality_rating}/5
{notes_section}

Generate a brief, friendly confirmation message that:
1. Summarizes what we're about to log
2. Asks for confirmation: "Does this look right?"
3. Mentions they can say "yes" to confirm or provide corrections

Keep it casual and encouraging!

Example:
"Great! Let me confirm - you studied **Assignment 1: RL Project** for **90 minutes** (1.5 hours), with focus level **4/5** and quality **4/5**. You noted: 'Made good progress on the algorithm.' Does this look right? Say 'yes' to log it, or let me know what to change!"
"""


GENERATE_SUCCESS_MESSAGE_PROMPT = """You are congratulating a student on completing a study session.

Just logged:
- Assignment: {assignment_name}
- Duration: {minutes} minutes ({hours} hours)
- Total hours done: {total_hours_done}
- Hours remaining: {hours_remaining}
- Current status: {status}

Additional context:
- Focus level: {focus_rating}/5
- Quality level: {quality_rating}/5
- Recent average focus: {recent_focus_avg}/5
- Recent average quality: {recent_quality_avg}/5

Generate an encouraging, personalized message that:
1. Confirms the logging: "✅ Logged 1.5 hours on Assignment 1!"
2. Shows progress: "You've now completed X hours, Y hours remaining"
3. Adds encouraging context based on ratings:
   - If high focus/quality: celebrate it! "Great focus! 🔥"
   - If low quality: be supportive "Having trouble? Remember you can ask for help!"
   - If they're making good progress: motivate them "You're on track! Keep going! 💪"
4. Keep it brief and emoji-friendly

Examples:
- "✅ Logged 1.5 hours on **RL Project**! You've completed 3.5 hours total, 6.5 hours remaining. Excellent focus (4/5) - keep up the great work! 🎯"
- "✅ Logged 2 hours on **Assignment 2**! You're now at 5/8 hours done. I noticed you got stuck this session (quality 2/5) - would you like me to find some resources to help? 💡"
"""
