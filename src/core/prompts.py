"""Prompts used for generating content with the Gemini API."""

PODCAST_ANALYSIS_STEP1_PROMPT = """
You are a podcast analysis assistant. I have provided you with a podcast episode. First, I need you to collect and organize key insights that we'll use to create a newsletter.

Please analyze the material and provide the following critical insights, and return only the <INSIGHTS> section:

<INSIGHTS>

1. Key Speakers:
- Identify the main speakers and their relevant backgrounds
- Note any significant guests or interviewees

2. Primary Thesis:
- What is the main argument or central theme of the episode?
- What is the core message or takeaway?

3. Current Context:
- How does this connect to current events or trends?
- What makes this conversation timely or relevant?

4. Key Points:
- What are the most surprising or provocative points raised?
- What are the major arguments or insights discussed?

5. Supporting Evidence:
- What specific anecdotes or examples were used?
- What data or research was referenced?

6. Episode Dynamics:
- What are the key dynamics or interactions between the speakers?
- What are the most interesting or surprising moments?

7. Notable Quotes:
- What are the most impactful or memorable quotes? Can be multiple sentences. (Avoid spoilers)
- Who said them and in what context?

</INSIGHTS>

Please organize your response under these headings and provide clear, detailed insights that we can use to craft the newsletter.
"""

PODCAST_ANALYSIS_STEP2_PROMPT = """
Using the insights provided from our first analysis, craft a compelling newsletter that will engage and inform our readers.

**Tone**:
- Adopt the tone of a young, hip, super-smart person. Your style should be casual and effortless, not formal and stodgy. No ten-dollar words.
- Write like someone would chat with a close friend about something they're really excited about.
- Be punchy and direct. Avoid clichés, cheesiness, or formal language.
- Ascribe political stances or phrases (e.g. "Republicans' cruelty," "Democrats' stupidity") to the hosts and guests—do not adopt them yourself.
- Do not spoil any major reveals or key moments.

Format your newsletter exactly as follows:

<NEWSLETTER>

**TLDR**
[Write one concise yet powerful sentence that captures the essence of the episode. If it's an interview, name the guests, the topic, and the general vibe.]

**BIG PICTURE**  
[Write one concise sentence that explains how the episode's themes fit into broader societal, cultural, or industry trends—provide connections or implications that make listeners think more deeply.]

**HIGHLIGHTS**  
- [A key idea, insightful theme, or unexpected point; include a short anecdote if relevant. Be specific.]  
- [Another standout point, observation, or turning point in the conversation. Be specific.]  
- [Optional if needed; focus on a surprising or revealing moment that adds nuance. Be specific.]

**QUOTED**  
"Insert the most memorable or revealing line here" —Speaker and brief speaker description [Quote a podcast guest, not the host, if there is one. Be careful not to quote a line from a clip played during the episode. Make sure the quote stands alone and makes sense in the context of the newsletter, to a reader who hasn't heard it. Quotes can be multiple sentences if needed.]

**WORTH YOUR TIME IF**  
You... [List types of listeners who would find this episode relevant or entertaining, e.g., “You're looking for a challenging conversation about foreign policy,” etc. Make non-obvious connections (e.g., a conversation about AI will always interest a tech nerd; that's not interesting), and make sure your suggestion is specific to the _episode,_ not the podcast series as a whole.]

</NEWSLETTER>

Your response should include **only the fully formatted newsletter** using the <NEWSLETTER> format. Do not include any additional text.
"""