import type { StoryMessage } from '../api/endpoints';

function extractNarrative(message: StoryMessage): string {
  if (message.ai_raw_response) {
    try {
      const parsed = JSON.parse(message.ai_raw_response) as { narrative?: unknown };
      if (typeof parsed.narrative === 'string' && parsed.narrative.trim()) {
        return parsed.narrative.trim();
      }
    } catch {
      // Older stories may not have structured director output.
    }
  }
  return (message.content || '').split(/\n\s*\n/, 1)[0].trim();
}

/** Convert the co-creation transcript into story paragraphs without role labels. */
export function buildStoryParagraphs(messages: StoryMessage[]): string[] {
  const aiTurns = new Set(
    messages
      .filter((message) => message.role === 'ai' && extractNarrative(message))
      .map((message) => message.turn_number),
  );

  return messages.flatMap((message) => {
    const text = message.role === 'ai'
      ? extractNarrative(message)
      : aiTurns.has(message.turn_number) ? '' : message.content.trim();
    if (!text) return [];
    return text.split(/\n\s*\n/).map((paragraph) => paragraph.trim()).filter(Boolean);
  });
}

export function buildCompleteStoryText(messages: StoryMessage[]): string {
  return buildStoryParagraphs(messages).join('\n\n');
}
