const OPENAI_ENDPOINT = 'https://api.openai.com/v1/chat/completions';

async function runOpenAI({ apiKey, model, prompt, timeoutMs = 90000 }) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(OPENAI_ENDPOINT, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
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
      throw new Error(payload?.error?.message || 'OpenAI request failed.');
    }

    return {
      text: payload?.choices?.[0]?.message?.content?.trim() || '',
      usage: payload?.usage || null,
    };
  } finally {
    clearTimeout(timeout);
  }
}

module.exports = { runOpenAI };
