from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload
from datetime import datetime
import pytz
from typing import Optional, List, Dict
from src.database.models import Podcasts, Episodes

# Podcast Operations
async def get_podcast_by_id(db: AsyncSession, podcast_id: str, load_episodes: bool = False) -> Optional[Podcasts]:
    """Get a podcast by its ID with optional episode loading"""
    query = select(Podcasts)
    if load_episodes:
        query = query.options(selectinload(Podcasts.episodes))
    query = query.where(Podcasts.id == podcast_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_podcast_by_rss_url(db: AsyncSession, rss_url: str) -> Optional[Podcasts]:
    """Get a podcast by its RSS URL"""
    result = await db.execute(
        select(Podcasts).where(Podcasts.rss_url == rss_url)
    )
    return result.scalar_one_or_none()

async def create_podcast(db: AsyncSession, data: Dict) -> Podcasts:
    """Create a new podcast
    
    Args:
        db: Database session
        data: Dictionary containing podcast data
        
    Returns:
        Created Podcasts instance
        
    Raises:
        ValueError: If required fields are missing
    """
    required_fields = ['name', 'rss_url', 'category']
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        raise ValueError(f"Missing required podcast fields: {', '.join(missing_fields)}")
        
    podcast = Podcasts(**data)
    db.add(podcast)
    return podcast

async def list_podcasts(
    db: AsyncSession,
    with_episode_count: bool = False,
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """List podcasts with optional episode count"""
    query = select(Podcasts)
    if with_episode_count:
        query = query.add_columns(
            func.count(Episodes.id).label('episode_count')
        ).outerjoin(Episodes).group_by(Podcasts.id)
    
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    
    if with_episode_count:
        return [
            {**podcast.__dict__, 'episode_count': count}
            for podcast, count in result.all()
        ]
    return [podcast.__dict__ for podcast in result.scalars().all()]

# Episode Operations
async def get_episode_by_id(db: AsyncSession, episode_id: str, load_podcast: bool = False) -> Optional[Episodes]:
    """Get an episode by its ID"""
    query = select(Episodes)
    if load_podcast:
        query = query.options(selectinload(Episodes.podcast))
    query = query.where(Episodes.id == episode_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_episode_by_guid(db: AsyncSession, rss_guid: str) -> Optional[Episodes]:
    """Get an episode by its RSS GUID"""
    result = await db.execute(
        select(Episodes).where(Episodes.rss_guid == rss_guid)
    )
    return result.scalar_one_or_none()

async def create_episode(db: AsyncSession, data: Dict) -> Episodes:
    """Create a new episode
    
    Args:
        db: Database session
        data: Dictionary containing episode data
        
    Returns:
        Created Episodes instance
        
    Raises:
        ValueError: If required fields are missing
    """
    required_fields = ['podcast_id', 'rss_guid', 'title', 'publish_date']
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        raise ValueError(f"Missing required episode fields: {', '.join(missing_fields)}")
        
    if 'publish_date' in data and isinstance(data['publish_date'], str):
        data['publish_date'] = datetime.fromisoformat(data['publish_date'])
        
    episode = Episodes(**data)
    db.add(episode)
    return episode

async def get_podcast_episodes(
    db: AsyncSession,
    podcast_id: str,
    limit: int = 100,
    offset: int = 0
) -> List[Episodes]:
    """Get episodes for a specific podcast"""
    result = await db.execute(
        select(Episodes)
        .where(Episodes.podcast_id == podcast_id)
        .order_by(Episodes.publish_date.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()

async def get_recent_episodes(
    db: AsyncSession,
    limit: int = 20,
    load_podcast: bool = True
) -> List[Episodes]:
    """Get recent episodes across all podcasts"""
    query = select(Episodes).order_by(Episodes.publish_date.desc()).limit(limit)
    if load_podcast:
        query = query.options(selectinload(Episodes.podcast))
    result = await db.execute(query)
    return result.scalars().all()

async def get_unprocessed_episodes(
    db: AsyncSession,
    limit: int = 100,
    load_podcast: bool = False
) -> List[Episodes]:
    """Get episodes that haven't been processed yet (no created_at timestamp)"""
    query = select(Episodes).where(Episodes.created_at.is_(None))
    if load_podcast:
        query = query.options(selectinload(Episodes.podcast))
    query = query.order_by(Episodes.publish_date.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all() 
