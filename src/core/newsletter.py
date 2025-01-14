import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def format_newsletter(analyses):
    """Format multiple podcast analyses into a newsletter"""
    try:
        logger.info("Formatting newsletter...")
        today = datetime.now().strftime("%B %d")
        
        newsletter = f"""# Podcast Briefing
#### {today}

*Quick update on today's episodes:*

"""
        
        for podcast_name, analysis in analyses.items():
            # Format the analysis text to ensure proper spacing and bullet points
            formatted_analysis = analysis.replace("KEY POINTS:", "**KEY POINTS:**")
            formatted_analysis = formatted_analysis.replace("→", "▸")  # nicer bullet
            formatted_analysis = formatted_analysis.replace("TLDR:", "**TLDR:**")
            formatted_analysis = formatted_analysis.replace("WHY NOW:", "**WHY NOW:**")
            formatted_analysis = formatted_analysis.replace("QUOTED:", "**QUOTED:**")
            
            newsletter += f"""
---

## {podcast_name}

{formatted_analysis}
"""
        
        newsletter += """
---
"""
        return newsletter
    
    except Exception as e:
        logger.error(f"Error formatting newsletter: {str(e)}", exc_info=True)
        raise

def save_newsletter(newsletter_text, output_path=None):
    """Save the newsletter to a file"""
    try:
        if output_path is None:
            output_path = f"podcast_digest_{datetime.now().strftime('%Y%m%d')}.md"
        
        logger.info(f"Saving newsletter to: {output_path}")
        with open(output_path, 'w') as f:
            f.write(newsletter_text)
        
        logger.info("Newsletter saved successfully")
        return output_path
    
    except Exception as e:
        logger.error(f"Error saving newsletter: {str(e)}", exc_info=True)
        raise 