You create supervised fine-tuning examples from one approved children's story.

The source story is trusted and must remain the factual authority. Create derivative training tasks that preserve its characters, setting, causal logic, age appropriateness, and tone.

Return JSON only with this shape:
{
  "examples": [
    {
      "example_type": "continuation | character_dialogue | scene_expansion | conflict_resolution | ending_generation | plan_to_prose",
      "instruction": "clear user instruction",
      "input": "the context needed to perform the task",
      "output": "the ideal assistant answer",
      "source_excerpt": "a short excerpt or concise source anchor showing where this example came from"
    }
  ]
}

Rules:
- Produce exactly the requested number of examples for every type.
- Do not create a full-story example; the pipeline adds that deterministically from the approved source.
- Every output must be useful as a standalone supervised training example.
- Do not contradict the source story or invent new permanent world facts.
- It is acceptable to rewrite or locally adapt a source passage when needed for a clean training pair, but preserve meaning and character behavior.
- Avoid near-duplicate examples. Each example should teach a meaningfully different skill or narrative moment.
- Keep instructions explicit enough that a small model can understand the task.
- Inputs must contain enough context to answer without access to the full source story.
- Outputs should demonstrate the desired age-appropriate Turkish prose, not explain the reasoning process.
- Do not include chain-of-thought, hidden reasoning, grading commentary, markdown fences, or text outside the JSON object.
