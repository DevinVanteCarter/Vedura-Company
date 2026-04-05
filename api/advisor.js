export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { message } = req.body;
  if (!message) return res.status(400).json({ error: 'No message provided' });

  try {
    const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${process.env.GROQ_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'llama-3.1-8b-instant',
        max_tokens: 300,
        messages: [
          {
            role: 'system',
            content: `You are Vedura AI — a knowledgeable off-grid homesteading advisor. You help with:
- Plant health and gardening (diagnosis, care, harvesting, soil, pests)
- Solar power management and off-grid energy
- Water systems and conservation
- Food growing, preservation, and self-sufficiency
- General homesteading questions

Be direct and practical. Give specific actionable advice.
Stay focused on homesteading, plants, solar, and off-grid living.
If scan data is provided, reference it specifically.
If no scan data, just answer the homesteading question directly without mentioning scans.
Never say 'this isn't related to scan results' — just answer the question.
Keep responses under 4 sentences unless more detail is needed.`
          },
          { role: 'user', content: message }
        ]
      })
    });

    const data = await response.json();
    const reply = data.choices?.[0]?.message?.content || 'Sorry, I could not generate a response.';
    res.status(200).json({ reply });
  } catch (err) {
    res.status(500).json({ error: 'Advisor unavailable', details: err.message });
  }
}
