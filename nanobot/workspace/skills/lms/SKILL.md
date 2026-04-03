---
name: lms
description: Use LMS MCP tools for live course data
always: true
---

# LMS Skill

You have access to the Learning Management System (LMS) via MCP tools. Use them to provide accurate, live data about the course.

## Available Tools

| Tool | When to Use | Parameters |
|------|-------------|------------|
| `lms_labs` | List all available labs. Call this FIRST when the user asks about scores, pass rates, completion, groups, timeline, or top learners without naming a specific lab. | None |
| `lms_health` | Check if the LMS backend is healthy and how many items it has. Use when asked about system health. | None |
| `lms_pass_rates` | Get average scores and attempt counts per task for a specific lab. | `lab` (e.g., "lab-01") |
| `lms_completion_rate` | Get passed/total completion rate for a specific lab. | `lab` (e.g., "lab-01") |
| `lms_timeline` | Get submission timeline (date + count) for a lab. | `lab` (e.g., "lab-01") |
| `lms_groups` | Get group performance (avg score + student count) for a lab. | `lab` (e.g., "lab-01") |
| `lms_top_learners` | Get top learners by average score for a lab. Use `limit` param (default 5). | `lab`, `limit` |
| `lms_learners` | List all learners registered in the LMS. | None |
| `lms_sync_pipeline` | Trigger the ETL sync pipeline if data seems stale or empty. | None |
| `lms_labs` | Trigger the ETL sync pipeline if data seems stale or empty. | None |

## Strategy

1. **If the user asks for scores, pass rates, completion, groups, timeline, or top learners WITHOUT naming a lab:**
   - Call `lms_labs` first to get the list of available labs
   - If multiple labs exist, ask the user to choose one
   - Use each lab's title/label (as returned by `lms_labs`) as the user-facing label
   - Provide stable lab values (e.g., "lab-01", "lab-02") that can be reused in follow-up tool calls

2. **If a lab parameter is needed but not provided by the user:**
   - Ask the user which lab they mean before proceeding
   - Do NOT guess or pick a default lab

3. **When answering with numeric results:**
   - Format percentages clearly (e.g., "93.9%", not "0.939")
   - Include counts (e.g., "108 out of 115")
   - Keep the response concise — don't dump raw JSON

4. **When the user asks "what can you do?":**
   - Explain your current LMS tools: you can query live data about labs, scores, pass rates, completion rates, group performance, submission timelines, and top learners
   - Mention that you need a lab name for most analytics queries
   - Be clear about your limits: you can only query data, not modify it (except triggering sync)

5. **If the data seems empty or stale:**
   - Consider calling `lms_sync_pipeline` to refresh the data
   - Inform the user you're syncing and retry their query

## Response Format

- Keep responses concise and readable
- Use bullet points or short paragraphs, not raw JSON
- When showing lab choices, use a numbered list with short labels
- After retrieving data, summarize the key findings in 1–3 sentences
