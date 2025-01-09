from sqlalchemy.orm import Session
from . import models
from typing import Optional, List
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

# User operations
def create_user(db: Session, id: str, email: str) -> models.User:
    """Create a new user"""
    user = models.User(id=id, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user(db: Session, user_id: str) -> Optional[models.User]:
    """Get a user by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()

# Podcast operations
def create_podcast(
    db: Session,
    name: str,
    rss_url: str,
    publisher: Optional[str] = None,
    description: Optional[str] = None
) -> models.Podcast:
    """Create a new podcast"""
    podcast = models.Podcast(
        name=name,
        rss_url=rss_url,
        publisher=publisher,
        description=description
    )
    db.add(podcast)
    db.commit()
    db.refresh(podcast)
    return podcast

def get_podcast(db: Session, podcast_id: UUID) -> Optional[models.Podcast]:
    """Get a podcast by ID"""
    return db.query(models.Podcast).filter(models.Podcast.id == podcast_id).first()

def get_podcast_by_rss_url(db: Session, rss_url: str) -> Optional[models.Podcast]:
    """Get a podcast by RSS URL"""
    return db.query(models.Podcast).filter(models.Podcast.rss_url == rss_url).first()

# Episode operations
def create_episode(
    db: Session,
    podcast_id: UUID,
    rss_guid: str,
    title: str,
    publish_date: Optional[str] = None,
    summary: Optional[str] = None
) -> models.Episode:
    """Create a new episode"""
    episode = models.Episode(
        podcast_id=podcast_id,
        rss_guid=rss_guid,
        title=title,
        publish_date=publish_date,
        summary=summary
    )
    db.add(episode)
    db.commit()
    db.refresh(episode)
    return episode

def get_episode(db: Session, episode_id: UUID) -> Optional[models.Episode]:
    """Get an episode by ID"""
    return db.query(models.Episode).filter(models.Episode.id == episode_id).first()

def get_episode_by_guid(db: Session, podcast_id: UUID, rss_guid: str) -> Optional[models.Episode]:
    """Get an episode by its RSS GUID and podcast ID"""
    return db.query(models.Episode).filter(
        models.Episode.podcast_id == podcast_id,
        models.Episode.rss_guid == rss_guid
    ).first()

def update_episode_summary(db: Session, episode_id: UUID, summary: str) -> Optional[models.Episode]:
    """Update an episode's summary"""
    episode = get_episode(db, episode_id)
    if episode:
        episode.summary = summary
        db.commit()
        db.refresh(episode)
    return episode

def get_podcast_episodes(
    db: Session,
    podcast_id: UUID,
    limit: int = 10
) -> List[models.Episode]:
    """Get recent episodes for a specific podcast"""
    return db.query(models.Episode)\
        .filter(models.Episode.podcast_id == podcast_id)\
        .order_by(models.Episode.publish_date.desc())\
        .limit(limit)\
        .all()

# Subscription operations
def create_subscription(
    db: Session,
    user_id: str,
    podcast_id: UUID
) -> models.Subscription:
    """Create a new subscription"""
    subscription = models.Subscription(
        user_id=user_id,
        podcast_id=podcast_id
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription

def get_user_subscriptions(
    db: Session,
    user_id: str,
    active_only: bool = True
) -> List[models.Subscription]:
    """Get all subscriptions for a user"""
    query = db.query(models.Subscription)\
        .filter(models.Subscription.user_id == user_id)
    
    if active_only:
        query = query.filter(models.Subscription.active == True)
    
    return query.all()

def update_subscription_status(
    db: Session,
    user_id: str,
    podcast_id: UUID,
    active: bool
) -> Optional[models.Subscription]:
    """Update a subscription's active status"""
    subscription = db.query(models.Subscription)\
        .filter(
            models.Subscription.user_id == user_id,
            models.Subscription.podcast_id == podcast_id
        ).first()
    
    if subscription:
        subscription.active = active
        db.commit()
        db.refresh(subscription)
    
    return subscription 