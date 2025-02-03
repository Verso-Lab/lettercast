import asyncio
import argparse
import os
from handler import lambda_handler

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Process recent podcast episodes')
    parser.add_argument('-m', type=int, default=60,
                      help='Number of minutes to look back for new episodes (default: 60)')
    
    args = parser.parse_args()
    
    # Set environment variable for lambda_handler
    os.environ['CHECK_MINUTES'] = str(args.m)
    
    # Run the Lambda handler as if it was triggered by EventBridge
    result = asyncio.run(lambda_handler())
    print(result) 