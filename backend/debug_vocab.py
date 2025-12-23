#!/usr/bin/env python3
"""
Debug script to check vocabulary data for a specific user.
Run with: python debug_vocab.py
"""

import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timezone

async def main():
    from database.db import get_session_context
    from database.models import Vocabulary
    from sqlalchemy import select
    
    USER_ID = 132900318
    
    async with get_session_context() as session:
        # Get all vocabulary for this user
        result = await session.execute(
            select(Vocabulary).where(Vocabulary.user_id == USER_ID)
        )
        words = result.scalars().all()
        
        now = datetime.now(timezone.utc)
        
        print(f"\n=== Vocabulary for User {USER_ID} ===")
        print(f"Total words: {len(words)}")
        print(f"Current time (UTC): {now}\n")
        
        if not words:
            print("❌ NO WORDS FOUND - This is the problem!")
            print("   Either:")
            print("   1. Words were never added to the database")
            print("   2. Words are stored under different user_id")
            return
        
        print("Words detail:")
        for w in words:
            due = "✅ DUE" if (w.next_review is None or w.next_review <= now) else "⏰ FUTURE"
            print(f"  - {w.word_de}: next_review={w.next_review}, learned={w.learned} [{due}]")
        
        # Count due words
        due_count = sum(1 for w in words if w.next_review is None or w.next_review <= now)
        print(f"\n📊 Words due for review: {due_count}")

if __name__ == "__main__":
    asyncio.run(main())
