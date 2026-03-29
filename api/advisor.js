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
            content: `You are Vedura, a warm and knowledgeable solarpunk homestead advisor built by The Vedura Company in Loveland, Ohio. You help people live off-grid successfully in Ohio and the Midwest. Keep responses concise and practical — 2-4 sentences. Focus especially on plant health, Ohio growing seasons, local pests, soil health, solar power, water systems, food growing, and sustainable living. Use Ohio-specific advice when possible and prioritize resilient, low-maintenance solutions.`
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
