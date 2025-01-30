from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from datetime import datetime
import pytz
from typing import Optional, List, Dict
from .models import Podcast, Episode

async def get_podcast_by_id(db: AsyncSession, podcast_id: str, load_episodes: bool = False) -> Optional[Podcast]:
    """Get a podcast by its ID with optional episode loading"""
    query = select(Podcast)
    if load_episodes:
        query = query.options(selectinload(Podcast.episodes))
    query = query.where(Podcast.id == podcast_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_podcast_by_rss_url(db: AsyncSession, rss_url: str) -> Optional[Podcast]:
    """Get a podcast by its RSS URL"""
    result = await db.execute(
        select(Podcast)
        .where(Podcast.rss_url == rss_url)
    )
    return result.scalar_one_or_none()

async def create_podcast(db: AsyncSession, podcast_data: Dict) -> Podcast:
    """Create a new podcast"""
    podcast = Podcast(**podcast_data)
    db.add(podcast)
    return podcast

async def get_episode_by_guid(db: AsyncSession, rss_guid: str) -> Optional[Episode]:
    """Get an episode by its RSS GUID"""
    result = await db.execute(
        select(Episode)
        .where(Episode.rss_guid == rss_guid)
    )
    return result.scalar_one_or_none()

async def create_episode(db: AsyncSession, episode_data: Dict) -> Episode:
    """Create a new episode"""
    episode = Episode(**episode_data)
    db.add(episode)
    return episode

async def update_episode_processed(
    db: AsyncSession, 
    episode_id: str, 
    newsletter_path: str
) -> Optional[Episode]:
    """Update episode after processing"""
    now = datetime.now(pytz.UTC)
    stmt = (
        update(Episode)
        .where(Episode.id == episode_id)
        .values(
            processed_at=now,
            newsletter_path=newsletter_path,
            updated_at=now
        )
        .returning(Episode)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_unprocessed_episodes(
    db: AsyncSession,
    limit: int = 100,
    load_podcast: bool = False
) -> List[Episode]:
    """Get unprocessed episodes with optional podcast data"""
    query = select(Episode).where(Episode.processed_at.is_(None))
    if load_podcast:
        query = query.options(selectinload(Episode.podcast))
    query = query.order_by(Episode.publish_date.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all() 
