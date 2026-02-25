"""
Production-Grade NER-based Entity Extraction for News Intelligence
Implements strict company/organization filtering with dominance-based ranking
"""

import re
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Set
import warnings
warnings.filterwarnings('ignore')

# Use transformers-based NER (optional - fallback to pattern-based)
def load_ner_model():
    """
    Factory function to load the NER model safely.
    Returns: (pipeline, available_bool)
    """
    try:
        from transformers import pipeline
        import torch
        device = 0 if torch.cuda.is_available() else -1
        print(f"🚀 NER Pipeline using device: {'GPU' if device==0 else 'CPU'}")
        
        # Aggregation strategy simple merges sub-tokens (B-ORG, I-ORG) into one entity
        model = pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple", device=device)
        print("✅ Transformers NER loaded successfully")
        return model, True
    except Exception as e:
        print(f"⚠️ Transformers not available, using pattern-based extraction: {e}")
        return None, False

# Default global state - initially None
ner_pipeline = None
NER_AVAILABLE = False


class AdvancedNERExtractor:
    """
    Production-grade entity extractor with strict company/organization filtering
    """
    
    def __init__(self, ner_instance=None):
        # Use passed instance if available, otherwise fallback to global (which is likely None now)
        self.ner = ner_instance if ner_instance else ner_pipeline
        
        # STRICT: Publishers and news outlets to exclude
        self.excluded_publishers = {
            'reuters', 'bloomberg', 'cnbc', 'cnn', 'bbc', 'forbes', 'techcrunch',
            'times', 'post', 'guardian', 'journal', 'news', 'press', 'media',
            'tribune', 'herald', 'gazette', 'chronicle', 'observer', 'telegraph',
            'associated press', 'ap news', 'afp', 'pti', 'ani', 'ians'
        }
        
        # STRICT: Generic terms that are NOT companies
        self.generic_terms = {
            'government', 'police', 'court', 'hospital', 'university', 'school',
            'company', 'corporation', 'industry', 'market', 'sector', 'department',
            'ministry', 'office', 'bureau', 'agency', 'service', 'center',
            'institute', 'foundation', 'trust', 'group', 'team', 'committee',
            'council', 'board', 'commission', 'authority', 'people', 'public',
            'officials', 'sources', 'experts', 'analysts', 'investors', 'customers'
        }
        
        # STRICT: Location/country indicators
        self.location_indicators = {
            'india', 'indian', 'us', 'usa', 'uk', 'china', 'chinese', 'japan',
            'america', 'american', 'europe', 'european', 'asia', 'asian',
            'delhi', 'mumbai', 'bangalore', 'london', 'new york', 'beijing',
            'tokyo', 'singapore', 'dubai', 'california', 'texas'
        }
        
        # Known company suffixes for validation
        self.company_suffixes = {
            'inc', 'corp', 'ltd', 'llc', 'co', 'group', 'holdings', 'technologies',
            'systems', 'solutions', 'services', 'industries', 'enterprises',
            'international', 'global', 'motors', 'energy', 'pharma', 'labs'
        }
        
        # Main actor position indicators (headline structure)
        self.main_actor_positions = ['start', 'subject']  # First 3 words or subject position
    
    def _is_valid_company_name(self, entity: str) -> bool:
        """
        STRICT validation: Is this truly a company/organization name?
        """
        entity_lower = entity.lower().strip()
        
        # Rule 1: Exclude publishers
        if any(pub in entity_lower for pub in self.excluded_publishers):
            return False
        
        # Rule 2: Exclude generic terms (single word)
        if ' ' not in entity_lower and entity_lower in self.generic_terms:
            return False
        
        # Rule 3: Exclude locations
        if entity_lower in self.location_indicators:
            return False
        
        # Rule 4: Must be capitalized (proper noun)
        if not entity[0].isupper():
            return False
        
        # Rule 5: Minimum length
        if len(entity) < 2:
            return False
        
        # Rule 6: Cannot be all uppercase (likely acronym without context)
        if entity.isupper() and len(entity) < 3:
            return False
        
        # Rule 7: Cannot contain only numbers
        if re.match(r'^[\d\s\-\/]+$', entity):
            return False
        
        return True
    
    
    # Involvement scoring removed for simplicity as per user request
    def _calculate_involvement_score(self, entity: str, headline: str, position: int, total_words: int) -> float:
        return 1.0 # Default value since we only care about mentions now
    
    def extract_entities_ner(self, articles: List[Dict], progress_callback=None) -> Dict[str, Dict]:
        """
        Extract entities using NER with strict filtering and GPU BATCHING.
        Returns: {entity_name: {mentions, involvement_scores, headlines}}
        """
        entity_data = defaultdict(lambda: {
            'mentions': 0,
            'involvement_scores': [],
            'headlines': [],
            'article_count': 0,
            'sources': set()
        })
        
        total_articles = len(articles)
        
        # We will collect all chunks from all articles to process in one giant batch
        all_chunks_info = [] # List of tuples: (article_id, chunk_text, chunk_offset)
        
        for idx, article in enumerate(articles):
            headline = article.get('title', '')
            source = article.get('source', 'Unknown')
            full_text = article.get('full_text', '')
            summary = article.get('summary', '')
            
            text_parts = [headline]
            if summary and len(summary) > 10:
                text_parts.append(summary)
            if full_text and len(full_text) > 50 and full_text != summary:
                text_parts.append(full_text)
                
            combined_text = ". ".join(text_parts)
            if not combined_text or len(combined_text) < 10:
                continue
            
            # IMPROVED CHUNKING: Split by logical sentences to avoid severing entities
            # We use a simple regex split on punctuation, then group up to ~1000 chars
            sentences = re.split(r'(?<=[.!?])\s+', combined_text)
            current_chunk = ""
            chunk_offset = 0
            
            for sentence in sentences:
                if len(current_chunk) + len(sentence) < 1500:
                    current_chunk += sentence + " "
                else:
                    if current_chunk:
                        all_chunks_info.append((idx, current_chunk.strip(), chunk_offset))
                        chunk_offset += len(current_chunk)
                    current_chunk = sentence + " "
            
            if current_chunk:
                all_chunks_info.append((idx, current_chunk.strip(), chunk_offset))
                
        # Now process all chunks efficiently
        extracted_entities_by_article = defaultdict(list)
        
        if self.ner and all_chunks_info:
            print(f"🚀 Batch processing {len(all_chunks_info)} chunks for NER...")
            chunk_texts = [info[1] for info in all_chunks_info]
            
            try:
                # BATCH PROCESSING
                from transformers.pipelines.pt_utils import KeyDataset
                # To really use batch_size > 1 we pass it directly
                # Ensure device is set on model load!
                # Note: list of strings works with batch_size too
                batch_results = self.ner(chunk_texts, batch_size=32)
                
                # If there's only one chunk, it might return a dict instead of list of lists
                if isinstance(batch_results, list) and len(batch_results) > 0 and isinstance(batch_results[0], dict):
                    batch_results = [batch_results]
                
                for i, result_list in enumerate(batch_results):
                    article_id, _, offset = all_chunks_info[i]
                    if not isinstance(result_list, list):
                        continue
                        
                    for item in result_list:
                        if item['entity_group'] == 'ORG':
                            entity_text = item['word'].strip()
                            position = offset + item['start'] # rough position
                            extracted_entities_by_article[article_id].append((entity_text, position))
            except Exception as e:
                print(f"⚠️ GPU Batching failed, using fallback: {e}")
                for i, (_, chunk_text, offset) in enumerate(all_chunks_info):
                    entities = self._extract_with_patterns(chunk_text)
                    for e_text, e_pos in entities:
                        extracted_entities_by_article[all_chunks_info[i][0]].append((e_text, e_pos + offset))
        else:
            # Fallback
            for idx, chunk_text, offset in all_chunks_info:
                entities = self._extract_with_patterns(chunk_text)
                for e_text, e_pos in entities:
                    extracted_entities_by_article[idx].append((e_text, e_pos + offset))
                    
        # Now map the extracted entities back to our article stats
        for idx, article in enumerate(articles):
            if progress_callback:
                try: progress_callback(idx + 1, total_articles)
                except: pass
                
            entities = extracted_entities_by_article.get(idx, [])
            seen_in_article = set()
            headline = article.get('title', '')
            source = article.get('source', '')
            
            for entity_text, position in entities:
                if not self._is_valid_company_name(entity_text):
                    continue
                
                entity_key = entity_text
                
                entity_data[entity_key]['mentions'] += 1
                entity_data[entity_key]['involvement_scores'].append(1.0)
                
                if headline not in entity_data[entity_key]['headlines']:
                    entity_data[entity_key]['headlines'].append(headline)
                entity_data[entity_key]['sources'].add(source)

                if entity_key not in seen_in_article:
                    entity_data[entity_key]['article_count'] += 1
                    seen_in_article.add(entity_key)
        
        return dict(entity_data)
    
    def _extract_with_transformers(self, text: str) -> List[Tuple[str, int]]:
        """Extract ORG entities using transformers NER"""
        try:
            results = self.ner(text)
            entities = []
            
            for item in results:
                # STRICT: Only ORG entities
                if item['entity_group'] == 'ORG':
                    entity_text = item['word'].strip()
                    # Estimate position
                    position = len(text[:item['start']].split())
                    entities.append((entity_text, position))
            
            return entities
        except:
            return self._extract_with_patterns(text)
    
    def _extract_with_patterns(self, text: str) -> List[Tuple[str, int]]:
        """Fallback: Pattern-based extraction"""
        entities = []
        words = text.split()
        
        i = 0
        while i < len(words):
            # Look for capitalized sequences (2-4 words)
            if words[i][0].isupper():
                entity_words = [words[i]]
                j = i + 1
                
                while j < len(words) and j < i + 4:
                    if words[j][0].isupper() or words[j].lower() in self.company_suffixes:
                        entity_words.append(words[j])
                        j += 1
                    else:
                        break
                
                if len(entity_words) >= 1:
                    entity = ' '.join(entity_words)
                    entities.append((entity, i))
                    i = j
                else:
                    i += 1
            else:
                i += 1
        
        return entities
    
    def rank_by_dominance(self, entity_data: Dict[str, Dict], total_articles: int) -> List[Dict]:
        """
        Rank entities purely by MENTION COUNT (Frequency).
        Simple logic: More mentions = Higher rank.
        """
        ranked = []
        
        for entity, data in entity_data.items():
            mentions = data['mentions']
            article_count = data['article_count']
            
            # NOISE REMOVAL: Minimum threshold
            # If very few mentions, ignore unless it's a tiny dataset
            if mentions < 2 and total_articles > 10:
                continue
            
            ranked.append({
                'name': entity,
                'mentions': mentions,
                'articles': article_count,
                # 'dominance_score' kept for compatibility but equals mentions
                'dominance_score': mentions, 
                'entity_type': 'company'
            })
        
        # Sort by mentions (descending)
        ranked.sort(key=lambda x: x['mentions'], reverse=True)
        
        # Add ranks
        for i, item in enumerate(ranked, 1):
            item['rank'] = i
        
        return ranked


def extract_top_companies(articles: List[Dict], query: str, top_n: int = 10, ner_model=None, progress_callback=None) -> List[Dict]:
    """
    Main function: Extract top trending companies/organizations
    
    Args:
        articles: List of article dictionaries with 'title', 'source'
        query: Search query (for context)
        top_n: Number of top entities to return
        ner_model: Optional pre-loaded NER pipeline
        progress_callback: Optional function(current, total)
    
    Returns:
        List of top N companies ranked by dominance
    """
    if not articles:
        return []
    
    extractor = AdvancedNERExtractor(ner_instance=ner_model)
    
    # Step 1: Extract entities with NER
    entity_data = extractor.extract_entities_ner(articles, progress_callback=progress_callback)
    
    # Step 2: Rank them
    ranked_entities = extractor.rank_by_dominance(entity_data, len(articles))
    
    # Step 3: Filter out the query itself (if it appears)
    # e.g. if searching for "NVIDIA", we don't want NVIDIA to be #1 result usually, 
    # or maybe we do? Let's keep it but maybe flag it? 
    # Usually users want to see *related* entities.
    # For now, we return everything.
    
    return ranked_entities[:top_n]

    return ranked_entities[:top_n]


def analyze_specific_brands(articles: List[Dict], target_brands: List[str], other_brands: List[str] = None) -> Dict[str, Dict]:
    """
    Specifically looks for mentions of the provided brand names (and competitors).
    If other_brands is provided, mentions of those brands (not in target_brands) are aggregated into 'Others'.
    Returns a dictionary with deep analytics: mentions, articles, sources, timeline, sentiment.
    """
    if not articles or not target_brands:
        return {}
        
    try:
        from textblob import TextBlob
        HAS_TEXTBLOB = True
    except ImportError:
        HAS_TEXTBLOB = False
        
    # Initialize result structure
    results = {}
    display_brands = list(target_brands)
    
    # Filter other_brands to remove any that are in target_brands
    pool_brands = []
    if other_brands:
        target_set = {b.lower().strip() for b in target_brands}
        pool_brands = [b for b in other_brands if b.lower().strip() not in target_set]
        if pool_brands:
            display_brands.append("Others")
            
    for brand in display_brands:
        results[brand] = {
            "mentions": 0, 
            "articles": 0,
            "sources": defaultdict(int),
            "timeline": defaultdict(int),
            "sentiment": {"Positive": 0, "Neutral": 0, "Negative": 0},
            "sentiment_by_source": defaultdict(lambda: {"Positive": 0, "Neutral": 0, "Negative": 0}),
            "article_samples": {"Positive": [], "Neutral": [], "Negative": []}
        }
    
    import re
    import unicodedata
    from datetime import datetime

    def normalize_text(text: str) -> str:
        """Strip accents, handle special chars, and lowercase for optimal matching."""
        if not text: return ""
        text = str(text)
        text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
        return text.lower()

    # Pre-process brands
    normalized_target_map = {b.lower().strip(): b for b in target_brands}
    target_terms = list(normalized_target_map.keys())
    
    # Pre-process pool brands
    pool_terms = [b.lower().strip() for b in pool_brands]
    
    # Pre-compile regex patterns
    compiled_patterns = {}
    for term in target_terms + pool_terms:
        norm_term = normalize_text(term)
        escaped_parts = [re.escape(part) for part in norm_term.split()]
        pattern = r'(?<!\w)' + r'\s+'.join(escaped_parts) + r'(?!\w)'
        compiled_patterns[term] = re.compile(pattern)
    
    for article in articles:
        text_parts = []
        if article.get('title'): text_parts.append(str(article['title']))
        if article.get('summary'): text_parts.append(str(article['summary']))
        if article.get('full_text'): text_parts.append(str(article['full_text'])[:5000])
        
        raw_content = " ".join(text_parts)
        content = normalize_text(raw_content)
        if not content.strip(): continue
            
        source = article.get('source', 'Unknown')
        
        # Date parsing
        published_raw = article.get('published', '')
        date_key = "Unknown"
        if published_raw:
            try:
                # Expecting something like "Fri, 02 Jan 2026 05:03:15 GMT"
                # Strip time and parse
                dt_str = published_raw[:16].strip()
                pd = datetime.strptime(dt_str, "%a, %d %b %Y")
                date_key = pd.strftime("%Y-%m-%d")
            except:
                try:
                    from dateutil import parser
                    pd = parser.parse(published_raw)
                    date_key = pd.strftime("%Y-%m-%d")
                except: date_key = "Unknown"
        
        # Track which category got sentiment for this article to avoid overcounting 'Others' as multiple articles
        article_matches = set() # Stores "Others" or the specific Brand Name
            
        # 1. Check Target Brands
        for term in target_terms:
            matches = compiled_patterns[term].findall(content)
            if matches:
                brand_name = normalized_target_map[term]
                article_matches.add(brand_name)
                results[brand_name]["mentions"] += len(matches)
                results[brand_name]["articles"] += 1
                results[brand_name]["sources"][source] += len(matches)
                results[brand_name]["timeline"][date_key] += len(matches)
                
                if HAS_TEXTBLOB:
                    sentences = re.split(r'[.!?]\s+', raw_content)
                    for sentence in sentences:
                        if compiled_patterns[term].search(normalize_text(sentence)):
                            polarity = TextBlob(sentence).sentiment.polarity
                            sent_cat = "Positive" if polarity > 0.05 else ("Negative" if polarity < -0.05 else "Neutral")
                            results[brand_name]["sentiment"][sent_cat] += 1
                            results[brand_name]["sentiment_by_source"][source][sent_cat] += 1
                            if len(results[brand_name]["article_samples"][sent_cat]) < 20:
                                sample_ref = {"title": article.get('title', 'Unknown'), "source": source, "url": article.get('url', ''), "published": published_raw}
                                if sample_ref["url"] not in [s.get('url') for s in results[brand_name]["article_samples"][sent_cat]]:
                                    results[brand_name]["article_samples"][sent_cat].append(sample_ref)

        # 2. Check Pool Brands (Aggregate into 'Others')
        if pool_terms:
            others_mentions = 0
            others_found = False
            for term in pool_terms:
                matches = compiled_patterns[term].findall(content)
                if matches:
                    others_mentions += len(matches)
                    others_found = True
                    # Only do sentiment if we want details for Others too
                    if HAS_TEXTBLOB:
                        sentences = re.split(r'[.!?]\s+', raw_content)
                        for sentence in sentences:
                            if compiled_patterns[term].search(normalize_text(sentence)):
                                polarity = TextBlob(sentence).sentiment.polarity
                                sent_cat = "Positive" if polarity > 0.05 else ("Negative" if polarity < -0.05 else "Neutral")
                                results["Others"]["sentiment"][sent_cat] += 1
            
            if others_found:
                results["Others"]["mentions"] += others_mentions
                results["Others"]["articles"] += 1
                results["Others"]["sources"][source] += others_mentions
                results["Others"]["timeline"][date_key] += others_mentions

    # Clean up
    for brand in results:
        results[brand]["sources"] = dict(results[brand]["sources"])
        results[brand]["timeline"] = dict(results[brand]["timeline"])
        results[brand]["sentiment_by_source"] = dict(results[brand]["sentiment_by_source"])
                
    return results
