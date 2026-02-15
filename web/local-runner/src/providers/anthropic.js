const ANTHROPIC_ENDPOINT = 'https://api.anthropic.com/v1/messages';

async function runAnthropic({ apiKey, model, prompt, timeoutMs = 90000 }) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(ANTHROPIC_ENDPOINT, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model,
        max_tokens: 900,
        temperature: 0.1,
        messages: [
          {
            role: 'user',
            content: prompt,
          },
        ],
      }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload?.error?.message || 'Anthropic request failed.');
    }

    const text = Array.isArray(payload?.content)
      ? payload.content
          .filter((entry) => entry?.type === 'text')
          .map((entry) => entry.text)
          .join('\n')
          .trim()
      : '';

    return {
      text,
      usage: payload?.usage || null,
    };
  } finally {
    clearTimeout(timeout);
  }
}

module.exports = { runAnthropic };
