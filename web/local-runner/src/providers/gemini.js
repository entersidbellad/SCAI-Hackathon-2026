async function runGemini({ apiKey, model, prompt, timeoutMs = 90000 }) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const modelPath = model.startsWith('models/') ? model : `models/${model}`;
  const endpoint = `https://generativelanguage.googleapis.com/v1beta/${modelPath}:generateContent?key=${encodeURIComponent(apiKey)}`;

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        contents: [{ role: 'user', parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.1,
          maxOutputTokens: 900,
        },
      }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload?.error?.message || 'Gemini request failed.');
    }

    const text = payload?.candidates?.[0]?.content?.parts
      ?.map((part) => part?.text || '')
      .join('\n')
      .trim();

    return {
      text: text || '',
      usage: payload?.usageMetadata || null,
    };
  } finally {
    clearTimeout(timeout);
  }
}

module.exports = { runGemini };
