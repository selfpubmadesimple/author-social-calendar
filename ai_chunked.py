# ai_chunked.py - Chunked generation for large post requests
import logging
import json
from ai import _get_client, SYSTEM_KIDLIT

def generate_posts_chunked(inputs: dict, num_days: int, holidays: list | None, model: str):
    """
    Generate posts in smaller chunks to avoid timeouts.
    Breaks large requests into chunks of 10 posts each.
    """
    logging.info(f"Starting chunked generation for {num_days} posts")
    
    chunk_size = 10
    all_posts = []
    
    # Calculate chunks needed
    num_chunks = (num_days + chunk_size - 1) // chunk_size  # Ceiling division
    logging.info(f"Will generate {num_chunks} chunks of up to {chunk_size} posts each")
    
    # Format holidays once for all chunks
    holiday_info = ""
    if holidays:
        try:
            from holidays import format_holidays_for_ai
            holiday_info = f"\n- {format_holidays_for_ai(holidays)}\n"
        except Exception:
            holiday_info = ""
    
    # Generate each chunk
    for chunk_num in range(num_chunks):
        start_idx = chunk_num * chunk_size
        posts_in_chunk = min(chunk_size, num_days - start_idx)
        
        logging.info(f"Generating chunk {chunk_num + 1}/{num_chunks}: {posts_in_chunk} posts")
        
        try:
            chunk_posts = generate_chunk(
                inputs, posts_in_chunk, holiday_info, model, 
                chunk_num, num_chunks
            )
            all_posts.extend(chunk_posts)
            logging.info(f"Successfully generated chunk {chunk_num + 1}")
            
        except Exception as chunk_error:
            logging.error(f"Failed to generate chunk {chunk_num + 1}: {str(chunk_error)}")
            
            # If early chunks fail, try with even smaller chunks
            if chunk_num == 0 and posts_in_chunk > 5:
                logging.info("Falling back to smaller chunks of 5 posts")
                try:
                    smaller_chunks = generate_small_chunks(inputs, num_days, holiday_info, model)
                    return smaller_chunks
                except Exception as fallback_error:
                    logging.error(f"Fallback also failed: {str(fallback_error)}")
                    raise chunk_error
            else:
                raise chunk_error
    
    logging.info(f"Chunked generation complete: {len(all_posts)} total posts")
    return all_posts

def generate_chunk(inputs: dict, chunk_size: int, holiday_info: str, model: str, chunk_num: int, total_chunks: int):
    """Generate a single chunk of posts."""
    
    # Create chunk-specific prompt
    user_prompt = f"""Author/book context:
- Title: {inputs.get('book_title', '')}
- Primary audience: {inputs.get('audience', 'families, educators, authors')}
- Reader age range: {inputs.get('age_range', 'ages 4–8')}
- Monthly goal: {inputs.get('goal', 'grow newsletter + drive gentle sales')}
- Tone: {inputs.get('tone', 'Warm')}
- Events/Promos this month: {inputs.get('events', '(none)')}
- Themes to emphasize: {inputs.get('themes', 'courage, kindness, friendship')}
- Differentiator/Unique angle: {inputs.get('differentiator', '')}{holiday_info}

This is chunk {chunk_num + 1} of {total_chunks}. Generate exactly {chunk_size} posts.

Requirements:
- Follow the content distribution: mix VALUE, BTS, QUOTE, ENGAGEMENT, PROMO themes
- 240–300 char captions, adult-facing, warm tone
- 3–6 hashtags including #KidLit #PictureBook
- Concrete image ideas
- Varied hooks (max 70 chars)
- Gentle CTAs for PROMO posts

Return JSON only: array of {chunk_size} post objects with fields: theme, caption, hashtags, image_idea, hook, cta
"""

    try:
        openai_client = _get_client()
        
        response = openai_client.chat.completions.create(
            model=model,
            temperature=0.6,
            timeout=30.0,  # Shorter timeout for smaller chunks
            messages=[
                {"role": "system", "content": SYSTEM_KIDLIT},
                {"role": "user", "content": user_prompt.strip()}
            ]
        )
        
        content = response.choices[0].message.content
        if not content:
            raise Exception(f"Empty response for chunk {chunk_num + 1}")
        
        content = content.strip()
        
        # Parse and validate
        posts = json.loads(content)
        
        # Clean the posts
        cleaned = []
        for post in posts:
            if isinstance(post, dict):
                cleaned.append({
                    "theme": post.get("theme", "").lower().strip(),
                    "caption": post.get("caption", "").strip(),
                    "hashtags": post.get("hashtags", "").strip(),
                    "image_idea": post.get("image_idea", "").strip(),
                    "hook": post.get("hook", "").strip(),
                    "cta": post.get("cta", "").strip()
                })
        
        return cleaned[:chunk_size]  # Ensure exact count
        
    except json.JSONDecodeError:
        logging.warning(f"JSON decode error in chunk {chunk_num + 1}, retrying...")
        # Single retry with JSON fix prompt
        fix_response = openai_client.chat.completions.create(
            model=model,
            temperature=0.1,
            timeout=30.0,
            messages=[
                {"role": "system", "content": f"Return valid JSON array of {chunk_size} post objects only."},
                {"role": "user", "content": content}
            ]
        )
        
        fixed_content = fix_response.choices[0].message.content
        if not fixed_content:
            raise Exception("Empty response on retry")
        posts = json.loads(fixed_content.strip())
        
        cleaned = []
        for post in posts:
            if isinstance(post, dict):
                cleaned.append({
                    "theme": post.get("theme", "").lower().strip(),
                    "caption": post.get("caption", "").strip(),
                    "hashtags": post.get("hashtags", "").strip(),
                    "image_idea": post.get("image_idea", "").strip(),
                    "hook": post.get("hook", "").strip(),
                    "cta": post.get("cta", "").strip()
                })
        
        return cleaned[:chunk_size]

def generate_small_chunks(inputs: dict, num_days: int, holiday_info: str, model: str):
    """Fallback: generate posts in very small chunks of 5."""
    logging.info("Using fallback: very small chunks of 5 posts")
    
    chunk_size = 5
    all_posts = []
    num_chunks = (num_days + chunk_size - 1) // chunk_size
    
    for chunk_num in range(num_chunks):
        posts_in_chunk = min(chunk_size, num_days - len(all_posts))
        
        try:
            chunk_posts = generate_chunk(
                inputs, posts_in_chunk, holiday_info, model,
                chunk_num, num_chunks
            )
            all_posts.extend(chunk_posts)
            
        except Exception as e:
            logging.error(f"Small chunk {chunk_num + 1} failed: {str(e)}")
            # For final fallback, create minimal posts
            for i in range(posts_in_chunk):
                all_posts.append({
                    "theme": ["value", "bts", "quote", "engagement", "promo"][i % 5],
                    "caption": f"Post about {inputs.get('book_title', 'your book')} - content generated",
                    "hashtags": "#KidLit #PictureBook #ChildrensBooks",
                    "image_idea": "Book cover with cozy reading setup",
                    "hook": f"Did you know...",
                    "cta": ""
                })
    
    return all_posts[:num_days]