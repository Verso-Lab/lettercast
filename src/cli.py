from handler import lambda_handler

def main():
    """CLI entry point"""
    try:
        audio_source = input("Enter URL or leave blank for default test: ").strip()
        if not audio_source:
            audio_source = "https://nyt.simplecastaudio.com/3026b665-46df-4d18-98e9-d1ce16bbb1df/episodes/13afee65-055d-4e1c-b6dc-66fd08977f03/audio/128/default.mp3"
        lambda_handler(audio_source)
    except Exception as e:
        print(f"\nError: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()