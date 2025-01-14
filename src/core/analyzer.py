import os
import google.generativeai as genai
from pathlib import Path
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class PodcastAnalyzer:
    def __init__(self, api_key):
        """Initialize the analyzer with a Gemini API key"""
        logger.info("Initializing PodcastAnalyzer")
        
        if not api_key:
            logger.error("GEMINI_API_KEY not provided")
            raise ValueError("GEMINI_API_KEY not provided")
            
        genai.configure(api_key=api_key)
        logger.info("Gemini API configured successfully")
        
        # Create the model
        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config=generation_config,
        )
        logger.info("Gemini model initialized")
    
    def analyze_audio_detailed(self, audio_path):
        """First pass: Get detailed analysis of a podcast episode"""
        DETAILED_PROMPT = """Analyze this podcast episode in detail. Focus on capturing:

1. Main Topic & Context: What's being discussed and why it matters now
2. Key Arguments/Points: The most important ideas and insights shared
3. Notable Moments: Surprising facts, strong opinions, or memorable exchanges
4. Best Quotes: The most impactful or revealing statements (with speaker attribution)
5. Implications: The bigger picture takeaways or why this matters

Be thorough but clear - this is our source material for the final newsletter."""

        try:
            logger.info(f"Starting detailed analysis for: {audio_path}")
            
            # Read the audio file
            logger.info("Reading audio file...")
            audio_data = Path(audio_path).read_bytes()
            
            # Send the audio with the prompt
            logger.info("Sending audio to Gemini for detailed analysis...")
            start_time = time.time()
            
            response = self.model.generate_content([
                DETAILED_PROMPT,
                {
                    "mime_type": "audio/mp3",
                    "data": audio_data
                }
            ])
            
            logger.info(f"Detailed analysis completed in {time.time() - start_time:.1f} seconds")
            return response.text
                
        except Exception as e:
            logger.error(f"Error in detailed analysis: {str(e)}", exc_info=True)
            return f"Error in detailed analysis: {str(e)}"

    def generate_cohesive_newsletter(self, podcast_analyses):
        """Generate a cohesive newsletter from multiple podcast analyses"""
        NEWSLETTER_PROMPT = """Write a sharp, insider-style briefing based ONLY on the podcast episode analyses provided below.
Do not add any episodes or information that wasn't provided.

Start with this exact format:

# Today's Podcast Briefing

Hey! [One punchy line introeducing the briefing]

---

Then for each provided podcast analysis, format exactly like this:

## [Podcast Name]

TLDR: [One punchy line that nails what this episode is really about]

WHY NOW: [Quick context on the timing/relevance]

KEY POINTS:
→ [First insight - be specific and surprising]
→ [Second insight - focus on what's newsworthy]
→ [Third insight - highlight what matters most]

QUOTED: "[Choose the single most powerful quote]" —[Speaker]

---

That's it. Hear ya later!

-------

Keep it tight and conversational. No jargon, no fluff. Write ONLY about the podcasts provided in the analysis."""

        try:
            logger.info(f"Generating newsletter from {len(podcast_analyses)} analyses...")
            start_time = time.time()
            
            # Prepare the input by combining podcast name and analysis
            combined_input = "Here are the podcast episode analyses to include (and ONLY these):\n\n"
            for podcast_name, analysis in podcast_analyses.items():
                combined_input += f"# {podcast_name}\n\n{analysis}\n\n---\n\n"
            
            response = self.model.generate_content([
                NEWSLETTER_PROMPT,
                combined_input
            ])
            
            logger.info(f"Newsletter generated in {time.time() - start_time:.1f} seconds")
            return response.text
                
        except Exception as e:
            logger.error(f"Error generating newsletter: {str(e)}", exc_info=True)
            return f"Error generating newsletter: {str(e)}" 