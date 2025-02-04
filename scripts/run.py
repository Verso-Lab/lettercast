import asyncio
import argparse
import os
from src.handler import lambda_handler

# TODO: Interactive mode (-i) needs to be implemented separately from Lambda handler
# since Lambda code should stay focused on batch processing. Consider creating a
# separate CLI tool for interactive podcast processing.

async def main():
    parser = argparse.ArgumentParser(description='Process recent podcast episodes')
    parser.add_argument('-m', type=int, default=60,
                      help='Number of minutes to look back for new episodes (default: 60)')
    
    args = parser.parse_args()
    
    try:
        # Set time window for Lambda handler
        os.environ['CHECK_MINUTES'] = str(args.m)
        
        # Run batch processing
        result = await lambda_handler()
        print(result['body'])
    except Exception as e:
        print(f"\nError: {str(e)}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 