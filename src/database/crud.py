from typing import Optional, List
from uuid import UUID
import logging

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from .models import (
    Podcast, Episode, User, Subscription,
    PodcastBase, EpisodeBase, UserBase, SubscriptionBase
)

logger = logging.getLogger(__name__)

# Podcast Operations
async def get_podcast_by_id(db: AsyncSession, podcast_id: UUID) -> Optional[Podcast]:
    return await db.get(Podcast, podcast_id)

async def get_podcast_by_rss_url(db: AsyncSession, rss_url: str) -> Optional[Podcast]:
    logger.info(f"Searching for podcast with RSS URL: {rss_url}")
    statement = select(Podcast).where(Podcast.rss_url == rss_url)
    try:
        result = await db.exec(statement)
        if result is None:
            logger.warning("db.exec returned None")
            return None
        return result.first()
    except Exception as e:
        logger.error(f"Error in get_podcast_by_rss_url: {str(e)}", exc_info=True)
        raise

async def create_podcast(db: AsyncSession, podcast_data: PodcastBase) -> Podcast:
    logger.info("Starting podcast creation...")
    try:
        podcast = Podcast.model_validate(podcast_data)
        logger.info("Validated podcast data")
        db.add(podcast)
        logger.info("Added podcast to session")
        await db.commit()
        logger.info("Committed podcast to database")
        await db.refresh(podcast)
        logger.info("Refreshed podcast object")
        return podcast
    except Exception as e:
        logger.error(f"Error in create_podcast: {str(e)}", exc_info=True)
        raise

async def list_podcasts(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0
) -> List[Podcast]:
    statement = select(Podcast).offset(offset).limit(limit)
    result = await db.exec(statement)
    return result.all()

# Episode Operations
async def get_episode_by_id(db: AsyncSession, episode_id: UUID, load_podcast: bool = False) -> Optional[Episode]:
    query = select(Episode)
    if load_podcast:
        query = query.options(selectinload(Episode.podcast))
    query = query.where(Episode.id == episode_id)
    result = await db.exec(query)
    return result.first()

async def get_episode_by_guid(db: AsyncSession, rss_guid: str) -> Optional[Episode]:
    statement = select(Episode).where(Episode.rss_guid == rss_guid)
    result = await db.exec(statement)
    return result.first()

async def create_episode(db: AsyncSession, episode_data: EpisodeBase) -> Episode:
    episode = Episode.model_validate(episode_data)
    db.add(episode)
    await db.commit()
    await db.refresh(episode)
    return episode

async def get_podcast_episodes(
    db: AsyncSession,
    podcast_id: UUID,
    limit: int = 100,
    offset: int = 0
) -> List[Episode]:
    statement = select(Episode).where(Episode.podcast_id == podcast_id).order_by(Episode.publish_date.desc()).limit(limit).offset(offset)
    result = await db.exec(statement)
    return result.all()

async def get_recent_episodes(
    db: AsyncSession,
    limit: int = 20,
    load_podcast: bool = True
) -> List[Episode]:
    query = select(Episode).order_by(Episode.publish_date.desc()).limit(limit)
    if load_podcast:
        query = query.options(selectinload(Episode.podcast))
    result = await db.exec(query)
    return result.all()

async def get_unprocessed_episodes(
    db: AsyncSession,
    limit: int = 100,
    load_podcast: bool = False
) -> List[Episode]:
    query = select(Episode).where(Episode.created_at.is_(None))
    if load_podcast:
        query = query.options(selectinload(Episode.podcast))
    query = query.order_by(Episode.publish_date.desc()).limit(limit)
    result = await db.exec(query)
    return result.all() 