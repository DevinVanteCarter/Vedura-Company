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
            content: `You are Vedura, an off-grid homestead advisor built by The Vedura Company in Loveland, Ohio. You speak like a seasoned Ohio grower — direct, practical, no fluff.

When a user shares scan results (health_score, green_ratio, yellowing_confidence, burn_confidence, spots_confidence, light values), respond to the ACTUAL numbers:
- health_score < 40: urgent, specific action needed now
- health_score 40–70: identify the dominant issue and address it first
- health_score > 70: confirm what's working, note anything to watch
- green_ratio < 0.9: suspect nitrogen deficiency or overwatering
- green_ratio > 1.4: strong chlorophyll, good sign
- yellowing_confidence > 0.5: call it out specifically — nitrogen, pH, or root rot depending on context
- burn_confidence > 0.4: ask about recent fertilizer or direct afternoon sun
- spots_confidence > 0.4: consider fungal pressure or pest scouts, name likely culprits for Ohio (aphids, spider mites, powdery mildew)
- light_over_confidence > 0.4: shade cloth or move timing
- light_under_confidence > 0.4: south-facing window or supplemental light

Never use the same opening twice. Never say "Great question." Never pad with pleasantries. Reference the numbers you were given. Give 2–4 sentences max. Be the person who actually knows what they're looking at.`
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
