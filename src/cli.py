import pandas as pd
from handler import lambda_handler, load_podcasts
from core.scraper import Podcast

def display_podcasts(podcasts: list[Podcast]):
    """Display numbered list of podcasts"""
    print("\nAvailable podcasts:")
    print("-" * 50)
    for i, podcast in enumerate(podcasts):
        print(f"{i+1}. {podcast.podcast_name}")
    print("-" * 50)

def get_user_choice(max_choice: int) -> int:
    """Get valid podcast choice from user"""
    while True:
        try:
            choice = input(f"\nChoose a podcast (1-{max_choice}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= max_choice:
                return choice_num - 1  # Convert to 0-based index
            print(f"Please enter a number between 1 and {max_choice}")
        except ValueError:
            print("Please enter a valid number")

def main():
    """CLI entry point"""
    try:
        # Load all podcasts
        podcasts = load_podcasts()
        
        # Display podcasts and get user choice
        display_podcasts(podcasts)
        choice = get_user_choice(len(podcasts))
        chosen_podcast = podcasts[choice]
        
        print(f"\nAnalyzing latest episode of: {chosen_podcast.podcast_name}")
        
        # Create event with single podcast
        event = {
            "single_podcast": True,
            "podcast": chosen_podcast
        }
        
        # Process podcast
        result = lambda_handler(event, None)
        
        if result['statusCode'] == 200:
            body = result['body']
            results = eval(body)['results']  # Safe since we control the input
            
            if results and results[0]['status'] == 'success':
                print("\nNewsletter generated successfully!")
                print(f"Output saved to: {results[0]['output_path']}")
                print("\nNewsletter content:")
                print("=" * 80)
                print(results[0]['newsletter'])
                print("=" * 80)
            else:
                print("\nError processing podcast:")
                print(results[0].get('error', 'Unknown error occurred'))
        else:
            print(f"\nError: {result.get('body', 'Unknown error occurred')}")
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()