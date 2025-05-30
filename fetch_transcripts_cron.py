#!/usr/bin/env python3
# fetch_transcripts_cron.py
"""
Cron script to fetch YouTube transcripts daily
Add to crontab: 0 2 * * * /usr/bin/python3 /path/to/fetch_transcripts_cron.py
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
log_file = Path(__file__).parent / 'cron.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

# Add project to path
sys.path.append(str(Path(__file__).parent))

from youtube_transcripts.config import DEFAULT_CHANNEL, DEFAULT_CLEANUP_MONTHS
from youtube_transcripts.core.database import initialize_database
from youtube_transcripts.core.transcript import process_channels

def main():
    """Main cron job function"""
    logging.info("Starting transcript fetch job")
    
    try:
        # Initialize database
        initialize_database()
        
        # Process default channels with 6-month cutoff
        channels = [DEFAULT_CHANNEL]
        date_cutoff = "6 months"
        
        logging.info(f"Processing channels: {channels}")
        processed, deleted = process_channels(
            channels, 
            date_cutoff, 
            DEFAULT_CLEANUP_MONTHS
        )
        
        logging.info(f"Processed {processed} transcripts, deleted {deleted} old ones")
        
    except Exception as e:
        logging.error(f"Error in cron job: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
