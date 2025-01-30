"""Prompts used for generating content with the Gemini API."""

PODCAST_DESCRIPTIONS = {
    "All-In": "A roundtable discussion between tech investors featuring rapid-fire debates and analysis of business, politics, and technology, with frequent use of industry jargon and references to market dynamics. The hosts frequently interrupt each other and use informal language, with conversations often branching into multiple simultaneous threads before being reined back in by the moderator. The show tends to favor free-market capitalism and tech-oriented solutions to social problems, with hosts representing varying political views from libertarian to moderate liberal. Co-host David Sacks is notably a prominent Trump advisor, which influences the show's political discussions.",
    "Call Her Daddy": "An explicitly candid podcast discussing relationships, sex, and social dynamics, characterized by informal language, explicit terminology, and personal anecdotes. The host frequently uses millennial/Gen-Z slang and internet culture references, with segments often structured around listener questions or viral social media topics.",
    "Conan O'Brien Needs a Friend": "A comedy interview show featuring long-form conversations that frequently derail into improvised bits and running jokes between Conan and his guests. The podcast maintains a loose structure where serious discussion about entertainment and creativity regularly gives way to absurdist humor and self-deprecating tangents.",
    "The Daily": "A highly produced news podcast following a consistent format of in-depth reporting on a single major story, featuring carefully scripted narration interwoven with interview clips and ambient sound. Each episode maintains a serious tone with clear transitions between segments, professional-quality audio, and minimal casual conversation.",
    "The Ezra Klein Show": "Long-form intellectual discussions with experts, characterized by methodical exploration of complex topics with frequent references to academic research and current events. The host consistently guides conversations through structured segments while pressing guests to clarify their positions and explore counterarguments. The show generally approaches topics from a progressive perspective while maintaining intellectual rigor.",
    "Fresh Air": "A professional interview program featuring in-depth conversations about arts and culture, with a focus on personal histories and creative processes. The host maintains a formal yet warm tone, asking carefully crafted questions that build upon previous responses while allowing for natural conversation flow.",
    "Hard Fork": "A technology news podcast combining analysis of current events with casual banter between hosts, featuring frequent references to Silicon Valley culture and tech industry dynamics. The conversation style alternates between serious discussion of technical concepts and lighthearted commentary, with hosts often challenging each other's perspectives.",
    "Huberman Lab": "A science-focused podcast delivering detailed explanations of human biology and neuroscience, with careful attention to breaking down complex concepts into digestible segments. The host maintains a methodical approach to topic exploration, frequently referring to specific research studies and using technical terminology while providing clear definitions. As part of the emerging alternative media ecosystem, the show sometimes platforms controversial views and challenges mainstream scientific consensus.",
    "The Joe Rogan Experience": "Long-form conversations covering a wide range of topics from comedy to politics to science, characterized by informal dialogue and frequent tangents. The host employs a conversational interview style with minimal structure, often sharing personal anecdotes and allowing discussions to evolve naturally over several hours. As one of the most prominent voices in alternative media, the show frequently features controversial guests and topics, sometimes promoting alternative viewpoints and conspiracy theories that challenge mainstream narratives.",
    "Lex Fridman Podcast": "In-depth interviews with experts across various fields, characterized by philosophical discussions and detailed technical explorations. The host maintains a consistently calm, methodical questioning style while pursuing deep discussions about consciousness, artificial intelligence, and human nature. As part of the alternative media landscape, the show often platforms controversial figures and alternative viewpoints that challenge establishment narratives.",
    "The Megyn Kelly Show": "A news commentary podcast featuring discussion of current events and political issues, with frequent guest interviews and analysis. The host maintains an assertive questioning style, often challenging guests' positions while incorporating personal opinions and references to her journalism background. The show generally leans conservative, frequently criticizing mainstream media narratives and progressive policies. As a prominent voice in alternative media, Kelly often platforms controversial guests and promotes skepticism of establishment institutions.",
    "The Mel Robbins Podcast": "A self-improvement focused podcast combining personal development advice with listener questions and expert interviews. The host frequently uses motivational language and shares personal anecdotes, maintaining an encouraging tone while providing actionable strategies.",
    "New Heights With Jason & Travis Kelce": "A sports and entertainment podcast featuring casual conversations between two NFL player brothers, characterized by playful sibling banter and insider perspectives on professional football. The hosts frequently use sports terminology and inside jokes while discussing current events in both their personal and professional lives.",
    "Newsroom Robots": "A podcast analyzing the intersection of artificial intelligence and journalism, featuring discussions about technological innovations and their impact on news media. The conversations frequently include technical terminology related to both AI and journalism, with regular references to current events and industry trends.",
    "Pod Save America": "A political commentary podcast featuring former Obama staffers discussing current events with an explicitly progressive/liberal perspective and frequent use of humor. The hosts maintain a casual conversation style while analyzing political strategies and policy details, often incorporating insider knowledge of government operations and consistently advocating for Democratic Party positions.",
    "Talking Headways": "A transportation and urban planning podcast featuring detailed discussions of infrastructure projects, policy decisions, and city development. The host maintains a focused approach to exploring technical topics while incorporating expert interviews and specific case studies from various cities.",
    "This Past Weekend w/ Theo Von": "A comedy podcast featuring stream-of-consciousness storytelling and unconventional perspectives on everyday life, characterized by unique metaphors and Southern colloquialisms. The host frequently weaves between personal anecdotes and abstract observations, creating a distinctive conversational style that combines humor with occasional philosophical insights. As part of the alternative media ecosystem, Von often expresses skepticism toward mainstream narratives and occasionally promotes alternative viewpoints on current events.",
    "The Weekly Show with Jon Stewart": "A current events commentary podcast combining political analysis with satirical humor, featuring both monologues and guest interviews. The host maintains his characteristic style of using sarcasm and wit to discuss serious topics, frequently referencing media clips and current events while building comedic narratives. While maintaining a generally left-leaning perspective, the show often criticizes both conservative and liberal political establishments.",
    "WTF with Marc Maron": "An interview podcast featuring deep conversations with entertainers and cultural figures, characterized by personal revelations and exploration of creative processes. The host maintains a confessional style while drawing out guests' stories, frequently referencing his own experiences and building intimate dialogue through shared vulnerability.",
}

PREANALYSIS_PROMPT = """
You are a podcast analysis assistant. I have provided you with an episode of {podcast_name}.

Podcast description: {podcast_description}

First, I need you to collect and organize key insights that we'll use to create a newsletter. Keep the description in mind as you analyze the material and provide the following critical insights. Return only the <INSIGHTS> section:

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

NEWSLETTER_PROMPT = """
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
You... [List types of listeners who would find this episode relevant or entertaining, e.g., "You're looking for a challenging conversation about foreign policy," etc. Make non-obvious connections (e.g., a conversation about AI will always interest a tech nerd; that's not interesting), and make sure your suggestion is specific to the _episode,_ not the podcast series as a whole.]

</NEWSLETTER>

Your response should include **only the fully formatted newsletter** using the <NEWSLETTER> format. Do not include any additional text.
"""