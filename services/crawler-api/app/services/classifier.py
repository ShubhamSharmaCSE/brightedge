"""
Content classification service for topic detection.
"""

import re
from typing import List, Dict, Any
from collections import Counter
import structlog
from bs4 import BeautifulSoup

from shared.models import TopicClassification, PageMetadata
from app.core.config import settings

logger = structlog.get_logger()


class ContentClassifier:
    """Content classifier for topic detection and content categorization."""
    
    def __init__(self):
        # Predefined topic keywords (in a production system, this would be ML-based)
        self.topic_keywords = {
            'technology': [
                'software', 'technology', 'computer', 'programming', 'code', 'development',
                'api', 'database', 'server', 'cloud', 'ai', 'artificial intelligence',
                'machine learning', 'algorithm', 'data', 'analytics', 'digital'
            ],
            'business': [
                'business', 'company', 'corporate', 'enterprise', 'startup', 'entrepreneur',
                'marketing', 'sales', 'revenue', 'profit', 'investment', 'finance',
                'strategy', 'management', 'leadership', 'market', 'customer'
            ],
            'ecommerce': [
                'shop', 'buy', 'purchase', 'product', 'cart', 'checkout', 'payment',
                'shipping', 'delivery', 'order', 'price', 'discount', 'sale',
                'retail', 'store', 'marketplace', 'amazon', 'ebay'
            ],
            'news': [
                'news', 'breaking', 'report', 'journalist', 'article', 'story',
                'update', 'latest', 'headline', 'media', 'press', 'newspaper',
                'magazine', 'broadcast', 'coverage'
            ],
            'health': [
                'health', 'medical', 'doctor', 'hospital', 'medicine', 'treatment',
                'patient', 'disease', 'symptoms', 'diagnosis', 'therapy', 'wellness',
                'fitness', 'nutrition', 'diet', 'exercise'
            ],
            'education': [
                'education', 'school', 'university', 'college', 'student', 'teacher',
                'course', 'learning', 'study', 'academic', 'research', 'science',
                'knowledge', 'training', 'tutorial', 'lesson'
            ],
            'entertainment': [
                'movie', 'film', 'music', 'game', 'entertainment', 'celebrity',
                'actor', 'actress', 'director', 'album', 'song', 'concert',
                'theater', 'show', 'television', 'streaming'
            ],
            'sports': [
                'sports', 'football', 'basketball', 'baseball', 'soccer', 'tennis',
                'golf', 'hockey', 'athlete', 'team', 'game', 'match', 'championship',
                'league', 'tournament', 'olympics'
            ],
            'travel': [
                'travel', 'vacation', 'hotel', 'flight', 'destination', 'tourism',
                'trip', 'journey', 'adventure', 'booking', 'resort', 'restaurant',
                'attractions', 'sightseeing', 'guide'
            ],
            'food': [
                'food', 'recipe', 'cooking', 'restaurant', 'cuisine', 'dish',
                'meal', 'ingredients', 'chef', 'kitchen', 'dining', 'menu',
                'taste', 'flavor', 'nutrition', 'diet'
            ],
            'lifestyle': [
                'lifestyle', 'fashion', 'beauty', 'home', 'family', 'relationship',
                'parenting', 'wedding', 'personal', 'advice', 'tips', 'guide',
                'culture', 'society', 'community'
            ],
            'finance': [
                'finance', 'money', 'investment', 'stock', 'market', 'trading',
                'banking', 'loan', 'credit', 'debt', 'insurance', 'retirement',
                'savings', 'budget', 'economic', 'currency'
            ]
        }
        
        # Compile regex patterns for efficiency
        self.keyword_patterns = {}
        for topic, keywords in self.topic_keywords.items():
            pattern = r'\b(?:' + '|'.join(re.escape(kw) for kw in keywords) + r')\b'
            self.keyword_patterns[topic] = re.compile(pattern, re.IGNORECASE)
    
    async def classify_content(self, soup: BeautifulSoup, metadata: PageMetadata) -> List[TopicClassification]:
        """Classify content and return topic classifications."""
        
        # Extract text content for analysis
        text_content = self._extract_text_content(soup)
        
        # Combine all text sources
        all_text = ' '.join(filter(None, [
            metadata.title or '',
            metadata.description or '',
            ' '.join(metadata.keywords),
            text_content
        ]))
        
        # Classify topics
        topic_scores = self._calculate_topic_scores(all_text)
        
        # Filter and format results
        classifications = []
        for topic, score in topic_scores.items():
            if score >= settings.MIN_TOPIC_CONFIDENCE:
                classification = TopicClassification(
                    topic=topic,
                    confidence=min(score, 1.0),  # Cap at 1.0
                    keywords=self._extract_topic_keywords(all_text, topic)
                )
                classifications.append(classification)
        
        # Sort by confidence and limit results
        classifications.sort(key=lambda x: x.confidence, reverse=True)
        return classifications[:settings.MAX_TOPICS_PER_PAGE]
    
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract clean text content from HTML."""
        # Remove script and style elements
        for element in soup(['script', 'style', 'head', 'title', 'meta']):
            element.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up text
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Limit text length to prevent memory issues
        return text[:10000]  # First 10K characters
    
    def _calculate_topic_scores(self, text: str) -> Dict[str, float]:
        """Calculate topic scores based on keyword matching."""
        text_lower = text.lower()
        word_count = len(text.split())
        
        if word_count == 0:
            return {}
        
        topic_scores = {}
        
        for topic, pattern in self.keyword_patterns.items():
            matches = pattern.findall(text_lower)
            
            if matches:
                # Calculate score based on:
                # 1. Number of matches
                # 2. Unique keywords matched
                # 3. Frequency relative to total word count
                
                unique_matches = set(matches)
                match_count = len(matches)
                unique_count = len(unique_matches)
                
                # Base score: unique keywords / total keywords for this topic
                base_score = unique_count / len(self.topic_keywords[topic])
                
                # Frequency boost: more matches = higher confidence
                frequency_boost = min(match_count / word_count * 100, 0.5)
                
                # Diversity boost: more unique keywords = higher confidence
                diversity_boost = min(unique_count / 10, 0.3)
                
                final_score = base_score + frequency_boost + diversity_boost
                topic_scores[topic] = final_score
        
        return topic_scores
    
    def _extract_topic_keywords(self, text: str, topic: str) -> List[str]:
        """Extract keywords that contributed to topic classification."""
        text_lower = text.lower()
        pattern = self.keyword_patterns.get(topic)
        
        if not pattern:
            return []
        
        matches = pattern.findall(text_lower)
        
        # Count occurrences and return top keywords
        keyword_counts = Counter(matches)
        top_keywords = [kw for kw, count in keyword_counts.most_common(5)]
        
        return top_keywords
    
    def classify_by_url(self, url: str) -> List[TopicClassification]:
        """Classify content based on URL patterns."""
        url_lower = url.lower()
        classifications = []
        
        # URL-based classification patterns
        url_patterns = {
            'ecommerce': ['/shop', '/buy', '/product', '/cart', '/checkout', 'amazon.com', 'ebay.com'],
            'news': ['/news', '/article', '/story', 'cnn.com', 'bbc.com', 'reuters.com'],
            'technology': ['/tech', '/software', '/api', '/docs', 'github.com', 'stackoverflow.com'],
            'business': ['/business', '/company', '/corporate', '/enterprise'],
            'education': ['/education', '/course', '/learn', '/tutorial', 'edu'],
            'entertainment': ['/entertainment', '/movie', '/music', '/game'],
            'sports': ['/sports', '/football', '/basketball', 'espn.com'],
            'travel': ['/travel', '/hotel', '/flight', '/vacation', 'booking.com'],
            'food': ['/food', '/recipe', '/restaurant', '/cooking'],
            'health': ['/health', '/medical', '/doctor', '/hospital'],
        }
        
        for topic, patterns in url_patterns.items():
            for pattern in patterns:
                if pattern in url_lower:
                    classification = TopicClassification(
                        topic=topic,
                        confidence=0.7,  # Medium confidence for URL-based classification
                        keywords=[pattern.strip('/')]
                    )
                    classifications.append(classification)
                    break
        
        return classifications
    
    def enhance_classification(self, classifications: List[TopicClassification], metadata: PageMetadata) -> List[TopicClassification]:
        """Enhance classifications with additional context."""
        
        # Add URL-based classifications
        url_classifications = self.classify_by_url(str(metadata.url))
        
        # Merge classifications
        classification_dict = {c.topic: c for c in classifications}
        
        for url_classification in url_classifications:
            if url_classification.topic in classification_dict:
                # Boost confidence if URL matches content classification
                existing = classification_dict[url_classification.topic]
                existing.confidence = min(existing.confidence + 0.2, 1.0)
            else:
                # Add new classification from URL
                classification_dict[url_classification.topic] = url_classification
        
        # Convert back to list and sort
        enhanced_classifications = list(classification_dict.values())
        enhanced_classifications.sort(key=lambda x: x.confidence, reverse=True)
        
        return enhanced_classifications[:settings.MAX_TOPICS_PER_PAGE]
