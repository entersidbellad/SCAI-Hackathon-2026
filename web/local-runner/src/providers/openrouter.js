const OPENROUTER_ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions';

async function runOpenRouter({ apiKey, model, prompt, timeoutMs = 90000 }) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(OPENROUTER_ENDPOINT, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
        'HTTP-Referer': 'http://127.0.0.1:8787',
        'X-Title': 'EVAL Local Runner',
      },
      body: JSON.stringify({
        model,
        temperature: 0.1,
        max_tokens: 900,
        messages: [
          {
            role: 'system',
            content:
              'You summarize legal/case text with high fidelity. Do not add facts not present in source.',
          },
          {
            role: 'user',
            content: prompt,
          },
        ],
      }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload?.error?.message || payload?.message || 'OpenRouter request failed.');
    }

    return {
      text: payload?.choices?.[0]?.message?.content?.trim() || '',
      usage: payload?.usage || null,
    };
  } finally {
    clearTimeout(timeout);
  }
}

module.exports = { runOpenRouter };
